# SPDX-License-Identifier: AGPL-3.0-or-later
import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api import __version__
from salubri_api.config import get_settings
from salubri_api.db import get_session
from salubri_api.models import Commune, PlanVersion
from salubri_api.services.dataset import dataset_key
from salubri_api.services.masking.detector import available as masking_available
from salubri_api.services.plan import trigger

router = APIRouter(tags=["Santé"])


@router.get("/health", summary="État du service, de la base, d'OSRM, de la carte et de la file de recalculs")
def health(s: Session = Depends(get_session)) -> dict[str, object]:
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
    queue: dict[str, int] = {"debounced": trigger.pending()}
    dataset = None
    if db == "ok":
        for st in ("pending", "running"):
            queue[st] = s.query(PlanVersion).filter(PlanVersion.status == st).count()
        c = s.query(Commune).first()
        dataset = dataset_key(s, c.id) if c else None
    return {
        "status": "ok" if db == "ok" else "degraded",
        "db": db,
        "osrm": osrm,
        "version": __version__,
        "demo_mode": get_settings().demo_mode,
        "dataset": dataset,  # carte chargée : routes-osm_… (vraies rues) ou routes-synthetiques_…
        "queue": queue,
        # masquage des visages et plaques (seconde passe serveur) : sans modèles, les photos sont refusées (503)
        # modules optionnels : les interfaces cachent ce qui est éteint
        "modules": {"seasons": get_settings().seasons_enabled, "assistant": get_settings().assistant_enabled},
        "masking": "ok"
        if masking_available()
        else "indisponible",  # recalculs en attente : la répétition attend qu'ils soient tous finis
    }
