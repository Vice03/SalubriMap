# SPDX-License-Identifier: AGPL-3.0-or-later
"""Retenues d'eau (barrages, lacs, marigots en surface ; OpenStreetMap) et dépotoirs qui les menacent.

Un dépotoir au bord d'une retenue pollue l'eau : lixiviats, plastiques emportés par les pluies, eau qui sert aussi
à l'arrosage et parfois à boire. Lecture publique, comme la carte."""

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api.db import get_session
from salubri_api.models import Commune
from salubri_api.routers.deps import get_commune

router = APIRouter(prefix="/eau", tags=["Eau"])

MIN_AREA_M2 = 5000  # une « retenue » : plan d'eau d'au moins un demi-hectare


@router.get("", summary="Retenues d'eau de la commune (FeatureCollection, polygones OSM d'au moins 0,5 ha)")
def retenues(s: Session = Depends(get_session), commune: Commune = Depends(get_commune)) -> dict[str, Any]:
    rows = s.execute(
        text("""SELECT id, kind, name, area_m2, ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, 0.00005)) AS g
                FROM water WHERE commune_id = :c AND kind IN ('water', 'wetland') AND area_m2 >= :a
                ORDER BY area_m2 DESC"""),
        {"c": commune.id, "a": MIN_AREA_M2},
    ).all()
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": str(r.id),
                "geometry": json.loads(r.g),
                "properties": {
                    "id": str(r.id),
                    "nom": r.name or ("Zone humide" if r.kind == "wetland" else "Retenue d'eau"),
                    "type": r.kind,
                    "surface_ha": round(r.area_m2 / 10000, 1),
                },
            }
            for r in rows
        ],  # fmt: skip
        "attribution": "© contributeurs OpenStreetMap (ODbL)",
    }


@router.get(
    "/depotoirs", summary="Dépotoirs actifs à moins de `distance_m` d'une retenue d'eau, du plus proche au plus loin"
)
def depotoirs_pres_de_l_eau(
    distance_m: Annotated[int, Query(ge=10, le=1000)] = 200,
    s: Session = Depends(get_session),
    commune: Commune = Depends(get_commune),
) -> dict[str, Any]:
    rows = s.execute(
        text("""SELECT DISTINCT ON (d.id) d.id, ST_X(d.geom) AS lon, ST_Y(d.geom) AS lat, d.status, d.volume_est_m3,
                       d.dominant_type, d.n_reports, d.near_drain, w.name AS retenue, w.id AS retenue_id,
                       round(ST_Distance(d.geom::geography, w.geom::geography)::numeric, 0) AS distance_m
                FROM dump_sites d JOIN water w
                  ON w.commune_id = d.commune_id AND w.kind IN ('water', 'wetland') AND w.area_m2 >= :a
                 AND ST_DWithin(w.geom, d.geom, :deg)
                 AND ST_DWithin(w.geom::geography, d.geom::geography, :d)
                WHERE d.commune_id = :c AND d.status IN ('active', 'recurring')
                ORDER BY d.id, distance_m"""),
        {"c": commune.id, "a": MIN_AREA_M2, "d": distance_m, "deg": distance_m / 90000},
    ).all()
    sites = sorted(
        (
            {
                "id": str(r.id),
                "lon": round(r.lon, 6),
                "lat": round(r.lat, 6),
                "statut": r.status,
                "volume_m3": r.volume_est_m3,
                "type": r.dominant_type,
                "n_signalements": r.n_reports,
                "caniveau": bool(r.near_drain),
                "retenue": r.retenue or "Retenue d'eau sans nom",
                "retenue_id": str(r.retenue_id),
                "distance_m": float(r.distance_m),
            }
            for r in rows
        ),  # fmt: skip
        key=lambda x: x["distance_m"],
    )
    par_retenue: dict[str, dict[str, Any]] = {}
    for x in sites:
        z = par_retenue.setdefault(x["retenue_id"], {"retenue": x["retenue"], "depotoirs": 0, "volume_m3": 0.0})
        z["depotoirs"] += 1
        z["volume_m3"] = round(z["volume_m3"] + x["volume_m3"], 1)
    return {"distance_m": distance_m, "sites": sites,
            "retenues": sorted(par_retenue.values(), key=lambda z: -z["depotoirs"])}  # fmt: skip
