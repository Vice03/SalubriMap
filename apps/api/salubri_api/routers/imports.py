# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from salubri_api.db import get_session
from salubri_api.models import Commune, ImportBatch, Report
from salubri_api.models.audit import audit
from salubri_api.routers.deps import get_commune, parse_uuid
from salubri_api.schemas.imports import ImportResult
from salubri_api.services.consolidation import consolidate
from salubri_api.services.importers.run import run_import
from salubri_api.services.plan.trigger import reports_changed

router = APIRouter(prefix="/imports", tags=["Import"])


@router.post(
    "",
    response_model=ImportResult,
    summary="Importer un fichier GeoJSON, CSV ou ZIP (fichier + photos)",
    description="Chaque ligne passe par les mêmes règles qu'un signalement Salubri Go. "
    "`dry_run=true` simule l'import sans rien enregistrer. Voir docs/IMPORT.md.",
)
def create_import(
    file: Annotated[UploadFile, File()],
    format: Annotated[str, Form()] = "auto",
    dry_run: Annotated[bool, Form()] = False,
    uploaded_by: Annotated[str | None, Form()] = None,
    s: Session = Depends(get_session),
    commune: Commune = Depends(get_commune),
) -> ImportResult:
    content = file.file.read()
    if not content:
        raise HTTPException(422, "Fichier vide")
    try:
        result = run_import(s, commune, file.filename or "import", content, format, dry_run, uploaded_by)
    except ValueError as exc:
        s.rollback()
        raise HTTPException(422, str(exc)) from exc
    if dry_run:
        s.rollback()
        return result
    consolidate(s, commune.id)
    audit(
        s,
        "import",
        "import_batch",
        result.batch_id,
        after={"file": file.filename, "accepted": result.accepted, "rejected": result.rejected},
    )
    s.commit()
    reports_changed(commune.id)
    return result


@router.get("", summary="Historique des imports")
def list_imports(s: Session = Depends(get_session)) -> list[dict[str, Any]]:
    return [
        {
            "id": str(b.id),
            "filename": b.filename,
            "format": b.format,
            "rows_total": b.rows_total,
            "accepted": b.rows_accepted,
            "rejected": b.rows_rejected,
            "rolled_back": b.rolled_back,
            "created_at": b.created_at.isoformat(),
        }
        for b in s.query(ImportBatch).order_by(ImportBatch.created_at.desc()).limit(100)
    ]


@router.get("/{batch_id}", summary="Rapport détaillé d'un import")
def get_import(batch_id: str, s: Session = Depends(get_session)) -> dict[str, Any]:
    b = s.get(ImportBatch, parse_uuid(batch_id, "import"))
    if b is None:
        raise HTTPException(404, "Import introuvable")
    return {
        "id": str(b.id),
        "filename": b.filename,
        "format": b.format,
        "rows_total": b.rows_total,
        "accepted": b.rows_accepted,
        "rejected": b.rows_rejected,
        "rolled_back": b.rolled_back,
        "report": b.report.get("rows", []),
    }


@router.post("/{batch_id}/rollback", summary="Annuler un import (supprime ses signalements)")
def rollback(
    batch_id: str, s: Session = Depends(get_session), commune: Commune = Depends(get_commune)
) -> dict[str, Any]:
    b = s.get(ImportBatch, parse_uuid(batch_id, "import"))
    if b is None:
        raise HTTPException(404, "Import introuvable")
    if b.rolled_back:
        return {"reverted": 0, "already": True}
    n = s.query(Report).filter(Report.import_batch_id == b.id).delete(synchronize_session=False)
    b.rolled_back = True
    audit(s, "rollback", "import_batch", b.id, after={"reverted": n})
    s.flush()
    consolidate(s, commune.id)
    s.commit()
    reports_changed(commune.id)
    return {"reverted": n, "already": False}
