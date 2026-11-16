# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from salubri_api.db import get_session
from salubri_api.models import SimRun
from salubri_api.routers.deps import parse_uuid

router = APIRouter(prefix="/sim-runs", tags=["Simulation"])


@router.get("/{run_id}", summary="Résultat de réplications : médiane, p10, p90 par indicateur")
def get_run(run_id: str, s: Session = Depends(get_session)) -> dict[str, Any]:
    r = s.get(SimRun, parse_uuid(run_id, "simulation"))
    if r is None:
        raise HTTPException(404, "Simulation introuvable")
    return {
        "id": str(r.id),
        "plan_id": str(r.plan_version_id),
        "status": r.status,
        "seed": r.seed,
        "horizon_days": r.horizon_days,
        "replications": r.replications,
        "metrics_summary": r.metrics_summary,
        "metrics_daily": r.metrics_daily,
        "duration_ms": r.duration_ms,
        "error": r.error,
    }
