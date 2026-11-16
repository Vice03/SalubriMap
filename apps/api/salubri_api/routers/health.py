# SPDX-License-Identifier: AGPL-3.0-or-later
import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api import __version__
from salubri_api.config import get_settings
from salubri_api.db import get_session

router = APIRouter(tags=["Santé"])


@router.get("/health", summary="État du service, de la base et d'OSRM")
def health(s: Session = Depends(get_session)) -> dict[str, str | bool]:
    try:
        s.execute(text("SELECT 1"))
        db = "ok"
    except Exception:
        db = "down"
    try:
        r = httpx.get(f"{get_settings().osrm_url}/nearest/v1/driving/-1.52,12.37", timeout=0.5)
        osrm = "ok" if r.status_code == 200 else "down"
    except Exception:
        osrm = "down"
    return {
        "status": "ok" if db == "ok" else "degraded",
        "db": db,
        "osrm": osrm,
        "version": __version__,
        "demo_mode": get_settings().demo_mode,
    }
