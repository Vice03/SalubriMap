# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Any

from fastapi import APIRouter, Depends

from salubri_api.models import Commune
from salubri_api.routers.deps import get_commune
from salubri_api.services.reports import thresholds_for
from salubri_api.services.validation.rules import all_rules

router = APIRouter(prefix="/validation", tags=["Validation"])


@router.get("/rules", summary="Règles anti-pièges R1–R12, seuils et pénalités (à afficher au jury)")
def rules(commune: Commune = Depends(get_commune)) -> dict[str, Any]:
    th = thresholds_for(commune)
    return {
        "start_score": 100,
        "status_thresholds": {"probable": th.probable_min, "to_review": th.review_min},
        "thresholds": th.model_dump(),
        "rules": [
            {"code": r.code, "title": r.title, "description": r.description, "penalty": r.penalty} for r in all_rules()
        ],
    }
