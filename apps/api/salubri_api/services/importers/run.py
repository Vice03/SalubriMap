# SPDX-License-Identifier: AGPL-3.0-or-later
"""Run an import: detect the format (GeoJSON, CSV or a zip holding one of them plus photos), stage, validate."""

import io
import zipfile

from geoalchemy2.shape import to_shape
from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api.models import Commune, ImportBatch
from salubri_api.schemas.imports import ImportResult, ImportRow
from salubri_api.services.importers.common import ParsedRow
from salubri_api.services.importers.csv import parse_csv
from salubri_api.services.importers.geojson import parse_geojson
from salubri_api.services.reports import Staged, stage_report, validate_staged

PHOTO_EXT = (".jpg", ".jpeg", ".png", ".webp")
# Lot A5 : garde-fous de l'archive (on ne l'extrait jamais sur le disque, tout reste en mémoire)
ZIP_MAX_ENTRIES = 2000
ZIP_MAX_TOTAL = 200 * 1024 * 1024  # taille décompressée totale
ZIP_MAX_ENTRY = 50 * 1024 * 1024  # un fichier de l'archive
ZIP_MAX_RATIO = 100  # taux de compression au-delà duquel un gros fichier est une bombe


def _safe_entries(z: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    """Vérifie l'archive avant toute lecture ; ValueError (message en français) si elle est suspecte."""
    infos = [i for i in z.infolist() if not i.is_dir()]
    if len(infos) > ZIP_MAX_ENTRIES:
        raise ValueError(f"Archive refusée : plus de {ZIP_MAX_ENTRIES} fichiers")
    total = 0
    for i in infos:
        name = i.filename.replace("\\", "/")
        if name.startswith("/") or ".." in name.split("/") or ":" in name.split("/")[0]:
            raise ValueError(f"Archive refusée : chemin interdit « {i.filename[:80]} »")
        if i.file_size > ZIP_MAX_ENTRY:
            raise ValueError(f"Archive refusée : « {i.filename[:80]} » dépasse {ZIP_MAX_ENTRY // (1024 * 1024)} Mo")
        if i.file_size > 1024 * 1024 and i.file_size > ZIP_MAX_RATIO * max(i.compress_size, 1):
            raise ValueError("Archive refusée : taux de compression anormal (bombe de décompression)")
        total += i.file_size
        if total > ZIP_MAX_TOTAL:
            raise ValueError(f"Archive refusée : plus de {ZIP_MAX_TOTAL // (1024 * 1024)} Mo une fois décompressée")
    return infos


def _read(z: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes:
    """Lit au plus la taille annoncée + 1 octet : une en-tête mensongère ne fait pas exploser la mémoire."""
    try:
        with z.open(info) as fh:
            data = fh.read(info.file_size + 1)
    except (zipfile.BadZipFile, EOFError, OSError) as exc:  # CRC faux, archive tronquée…
        raise ValueError(f"Archive refusée : « {info.filename[:80]} » est corrompu") from exc
    if len(data) > info.file_size:
        raise ValueError("Archive refusée : taille réelle différente de la taille annoncée")
    return data


def detect_and_parse(
    filename: str,
    content: bytes,
    fmt: str | None = None,
    photos: dict[str, bytes] | None = None,
    bbox: tuple[float, float, float, float] | None = None,
) -> tuple[str, list[ParsedRow]]:
    name = filename.lower()
    photos = dict(photos or {})
    if name.endswith(".zip") or content[:2] == b"PK":
        try:
            z = zipfile.ZipFile(io.BytesIO(content))
        except zipfile.BadZipFile as exc:
            raise ValueError("Archive ZIP illisible") from exc
        with z:
            data_info = None
            for i in _safe_entries(z):
                low = i.filename.lower()
                if low.endswith(PHOTO_EXT):
                    # seul le nom de base sert de clé ; il n'est jamais utilisé comme chemin sur le disque
                    photos[i.filename.replace("\\", "/").split("/")[-1]] = _read(z, i)
                elif low.endswith((".geojson", ".json", ".csv")) and data_info is None:
                    data_info = i
            if data_info is None:
                raise ValueError("L'archive ne contient ni .geojson ni .csv")
            name, content = data_info.filename.lower(), _read(z, data_info)
    if fmt in (None, "", "auto"):
        fmt = "csv" if name.endswith(".csv") else "geojson"
    if fmt == "csv":
        return "csv", parse_csv(content, photos, bbox)
    return "geojson", parse_geojson(content, photos, bbox)


def _duplicates_and_outside(s: Session, commune: Commune, parsed: list[ParsedRow]) -> None:
    """Lignes refusées avant tout enregistrement, avec un message clair : doublon dans le fichier, identifiant déjà
    importé. Un point hors de la commune est enregistré et rejeté par la règle R5, comme un signalement de Salubri Go
    (le jury doit le retrouver « rejeté ») ; la ligne porte la distance en avertissement."""
    seen: dict[object, int] = {}
    ok = [pr for pr in parsed if pr.data is not None]
    ids = [pr.data.external_id for pr in ok if pr.data and pr.data.external_id]
    known = (
        {
            r.external_id
            for r in s.execute(
                text("SELECT external_id FROM reports WHERE commune_id = :c AND external_id = ANY(:ids)"),
                {"c": commune.id, "ids": ids},
            )
        }
        if ids
        else set()
    )
    buf = float((commune.params_default or {}).get("validation", {}).get("zone_buffer_m", 500))
    dist = {}
    if ok and s.execute(text("SELECT count(*) FROM quartiers WHERE commune_id = :c"), {"c": commune.id}).scalar():
        rows = s.execute(
            text("""
            SELECT u.i, (SELECT min(ST_Distance(q.geom::geography, ST_SetSRID(ST_MakePoint(u.lon, u.lat), 4326)::geography))
                         FROM quartiers q WHERE q.commune_id = :c) AS d
            FROM unnest(CAST(:lons AS float8[]), CAST(:lats AS float8[])) WITH ORDINALITY AS u(lon, lat, i)"""),
            {"c": commune.id, "lons": [pr.data.lon for pr in ok], "lats": [pr.data.lat for pr in ok]},  # type: ignore[union-attr]
        ).all()
        dist = {ok[int(r.i) - 1].row: float(r.d) for r in rows}
    for pr in ok:
        d = pr.data
        assert d is not None
        problems = []
        if dist.get(pr.row, 0.0) > buf:
            pr.warnings.append(
                f"Hors de la commune : à {dist[pr.row] / 1000:.1f} km des quartiers (marge {buf:.0f} m), "
                f"point ({d.lat:.5f}, {d.lon:.5f}) — rejeté par la règle R5"
            )
        if d.external_id and d.external_id in known:
            problems.append(f"Déjà importé : l'identifiant « {d.external_id} » existe déjà dans la base")
        for key in (
            ("id", d.external_id) if d.external_id else None,
            ("pt", round(d.lat, 6), round(d.lon, 6), d.reported_at, d.waste_type, d.comment),
        ):
            if key is None:
                continue
            if key in seen:
                what = "même identifiant" if key[0] == "id" else "même point, même date, même type"
                problems.append(f"Doublon de la ligne {seen[key]} du fichier ({what})")
                break
            seen[key] = pr.row
        if problems:
            pr.data, pr.errors = None, problems


def run_import(
    s: Session,
    commune: Commune,
    filename: str,
    content: bytes,
    fmt: str | None,
    dry_run: bool,
    uploaded_by: str | None = None,
    photos: dict[str, bytes] | None = None,
) -> ImportResult:
    b = to_shape(commune.bbox).bounds if commune.bbox is not None else None
    fmt_used, parsed = detect_and_parse(filename, content, fmt, photos, b)
    info = getattr(parsed, "info", {})
    _duplicates_and_outside(s, commune, parsed)
    sp = s.begin_nested() if dry_run else None
    batch = ImportBatch(filename=filename[:256], format=fmt_used, uploaded_by=uploaded_by)
    s.add(batch)
    s.flush()
    staged: list[tuple[ParsedRow, Staged | None, list[str]]] = []
    for pr in parsed:
        if pr.data is None:
            staged.append((pr, None, pr.errors))
            continue
        try:
            staged.append((pr, stage_report(s, commune, pr.data, pr.photo_bytes, batch.id), []))
        except ValueError as exc:
            staged.append((pr, None, [str(exc)]))
    evals = validate_staged(s, commune, [st for _, st, _ in staged if st is not None])
    rows: list[ImportRow] = []
    for pr, st, errs in staged:
        if st is None:
            rows.append(ImportRow(row=pr.row, status="rejected", errors=errs, warnings=pr.warnings, external_id=None))
            continue
        ev = evals[st.report.id]
        rows.append(
            ImportRow(
                row=pr.row,
                status="accepted",
                warnings=pr.warnings,
                report_id=str(st.report.id),
                external_id=st.report.external_id,
                score=st.report.score,
                report_status=st.report.status,
                rule_hits=ev.hits_json,
            )
        )
    accepted = sum(1 for r in rows if r.status == "accepted")
    result = ImportResult(
        batch_id=None if dry_run else str(batch.id),
        dry_run=dry_run,
        format=fmt_used,
        rows_total=len(rows),
        accepted=accepted,
        rejected=len(rows) - accepted,
        report=rows,
        crs=info.get("crs"),
        colonnes=info.get("colonnes", {}),
    )
    if sp is not None:
        sp.rollback()
        return result
    batch.rows_total, batch.rows_accepted, batch.rows_rejected = result.rows_total, accepted, result.rejected
    batch.report = {"rows": [r.model_dump() for r in rows]}
    return result
