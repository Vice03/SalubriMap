# SPDX-License-Identifier: AGPL-3.0-or-later
"""Run an import: detect the format (GeoJSON, CSV or a zip holding one of them plus photos), stage, validate."""

import io
import zipfile

from sqlalchemy.orm import Session

from salubri_api.models import Commune, ImportBatch
from salubri_api.schemas.imports import ImportResult, ImportRow
from salubri_api.services.importers.common import ParsedRow
from salubri_api.services.importers.csv import parse_csv
from salubri_api.services.importers.geojson import parse_geojson
from salubri_api.services.masking import MaskingUnavailable
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
    filename: str, content: bytes, fmt: str | None = None, photos: dict[str, bytes] | None = None
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
        return "csv", parse_csv(content, photos)
    return "geojson", parse_geojson(content, photos)


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
    fmt_used, parsed = detect_and_parse(filename, content, fmt, photos)
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
        except MaskingUnavailable:
            # aucune photo d'import enregistrée sans masquage des visages et des plaques
            staged.append((pr, None, ["Masquage des visages indisponible sur le serveur : photo non importée"]))
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
    )
    if sp is not None:
        sp.rollback()
        return result
    batch.rows_total, batch.rows_accepted, batch.rows_rejected = result.rows_total, accepted, result.rejected
    batch.report = {"rows": [r.model_dump() for r in rows]}
    return result
