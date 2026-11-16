# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry import shape as geo_shape
from sqlalchemy import func
from sqlalchemy.orm import Session

from salubri_api.db import get_session
from salubri_api.models import Commune, Ilot, Quartier, Scenario
from salubri_api.models.audit import audit
from salubri_api.routers.deps import get_commune, require_admin
from salubri_api.services.geo import feature, feature_collection, to_wkb
from salubri_api.services.ilots import rebuild_ilots
from salubri_api.services.params import ScenarioParams
from salubri_api.services.plan.pipeline import request_recompute

router = APIRouter(prefix="/quartiers", tags=["Quartiers"], dependencies=[Depends(require_admin)])


class QuartierFeature(BaseModel):
    type: str = "Feature"
    geometry: dict[str, Any]
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="name (texte), population (entier), arrondissement (optionnel), "
        "scenario_id (optionnel : limite l'ajout à ce scénario)",
    )


@router.get("", summary="Quartiers (FeatureCollection avec population et nombre d'îlots)")
def list_quartiers(s: Session = Depends(get_session), commune: Commune = Depends(get_commune)) -> dict[str, Any]:
    counts = dict(s.query(Ilot.quartier_id, func.count()).group_by(Ilot.quartier_id).all())
    rows = s.query(Quartier).filter(Quartier.commune_id == commune.id).order_by(Quartier.name).all()
    return feature_collection(
        [
            feature(
                q.geom,
                {
                    "id": str(q.id),
                    "name": q.name,
                    "arrondissement": q.arrondissement,
                    "population": q.population,
                    "active": q.active,
                    "source": q.source,
                    "n_ilots": counts.get(q.id, 0),
                },
                q.id,
            )
            for q in rows
        ]
    )


@router.post("", status_code=201, summary="Ajouter un quartier (polygone dessiné) : recalcul incrémental des plans")
def create_quartier(
    body: QuartierFeature, s: Session = Depends(get_session), commune: Commune = Depends(get_commune)
) -> dict[str, Any]:
    try:
        geom = geo_shape(body.geometry)
    except Exception as exc:
        raise HTTPException(422, "Géométrie invalide") from exc
    if isinstance(geom, Polygon):
        geom = MultiPolygon([geom])
    if not isinstance(geom, MultiPolygon) or not geom.is_valid or geom.is_empty:
        raise HTTPException(422, "Un polygone valide est attendu")
    name = str(body.properties.get("name") or "Nouveau quartier")
    try:
        population = int(body.properties.get("population", 0))
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, "population doit être un entier") from exc
    if population <= 0:
        raise HTTPException(422, "population doit être > 0")
    q = Quartier(
        commune_id=commune.id,
        name=name,
        population=population,
        geom=to_wkb(geom),
        source="user",
        arrondissement=body.properties.get("arrondissement"),
    )
    s.add(q)
    s.flush()
    n = rebuild_ilots(s, q)
    audit(s, "create", "quartier", q.id, after={"name": name, "population": population, "ilots": n})
    plan_ids = []
    scenarios = s.query(Scenario).filter(Scenario.commune_id == commune.id).all()
    only = body.properties.get("scenario_id")
    if only:
        scenarios = [sc for sc in scenarios if str(sc.id) == str(only)]
        if not scenarios:
            raise HTTPException(404, "Scénario introuvable")
        for sc in s.query(Scenario).filter(Scenario.commune_id == commune.id).all():
            p = ScenarioParams(**(sc.params or {}))
            if str(sc.id) != str(only) and p.active_quartier_ids is None:
                # 'all quartiers' scenarios must not silently pick up a quartier meant for one scenario
                sc.params = {
                    **sc.params,
                    "active_quartier_ids": [
                        str(x.id)
                        for x in s.query(Quartier).filter(
                            Quartier.commune_id == commune.id, Quartier.id != q.id, Quartier.active.is_(True)
                        )
                    ],
                }
    for sc in scenarios:
        p = ScenarioParams(**(sc.params or {}))
        if p.active_quartier_ids is not None:
            sc.params = {**sc.params, "active_quartier_ids": [*p.active_quartier_ids, str(q.id)]}
    s.commit()
    for sc in scenarios:
        pv = request_recompute(s, sc, "zone_changed", {"quartier": name})
        plan_ids.append({"scenario_id": str(sc.id), "plan_version_id": str(pv.id)})
    return {
        "quartier": feature(q.geom, {"id": str(q.id), "name": q.name, "population": q.population, "n_ilots": n}, q.id),
        "plans": plan_ids,
    }


@router.delete(
    "/{quartier_id}", status_code=204, summary="Supprimer un quartier ajouté (les plans ne le comptent plus)"
)
def delete_quartier(
    quartier_id: str, s: Session = Depends(get_session), commune: Commune = Depends(get_commune)
) -> None:
    from salubri_api.routers.deps import parse_uuid

    q = s.get(Quartier, parse_uuid(quartier_id, "quartier"))
    if q is None or q.commune_id != commune.id:
        raise HTTPException(404, "Quartier introuvable")
    if q.source != "user":
        raise HTTPException(409, "Seuls les quartiers ajoutés depuis l'interface peuvent être supprimés")
    for sc in s.query(Scenario).filter(Scenario.commune_id == commune.id):
        p = ScenarioParams(**(sc.params or {}))
        if p.active_quartier_ids and str(q.id) in p.active_quartier_ids:
            sc.params = {**sc.params, "active_quartier_ids": [x for x in p.active_quartier_ids if x != str(q.id)]}
    audit(s, "delete", "quartier", q.id, before={"name": q.name})
    s.delete(q)
    s.commit()
