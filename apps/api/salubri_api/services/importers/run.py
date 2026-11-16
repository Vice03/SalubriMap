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
from salubri_api.services.reports import Staged, stage_report, validate_staged

PHOTO_EXT = (".jpg", ".jpeg", ".png", ".webp")


def detect_and_parse(
    filename: str, content: bytes, fmt: str | None = None, photos: dict[str, bytes] | None = None
) -> tuple[str, list[ParsedRow]]:
    name = filename.lower()
    photos = dict(photos or {})
    if name.endswith(".zip") or content[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            data_name = None
            for n in z.namelist():
                low = n.lower()
                if low.endswith(PHOTO_EXT):
                    photos[n.replace("\\", "/").split("/")[-1]] = z.read(n)
                elif low.endswith((".geojson", ".json", ".csv")) and data_name is None:
                    data_name = n
            if data_name is None:
                raise ValueError("L'archive ne contient ni .geojson ni .csv")
            name, content = data_name.lower(), z.read(data_name)
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
