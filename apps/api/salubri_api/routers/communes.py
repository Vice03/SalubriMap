# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from salubri_api.db import get_session
from salubri_api.models import Commune
from salubri_api.services.geo import shape

router = APIRouter(prefix="/communes", tags=["Commune"])


@router.get("/{slug}", summary="Commune : emprise, dépôt des camions, paramètres par défaut")
def get_commune_info(slug: str, s: Session = Depends(get_session)) -> dict[str, Any]:
    c = s.query(Commune).filter(Commune.slug == slug).first()
    if c is None:
        raise HTTPException(404, "Commune inconnue")
    b = shape(c.bbox).bounds
    d = shape(c.depot_geom)
    return {
        "id": str(c.id),
        "slug": c.slug,
        "name": c.name,
        "bbox": [b[0], b[1], b[2], b[3]],
        "center": [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2],
        "depot": [d.x, d.y],
        "params_default": c.params_default,
    }
