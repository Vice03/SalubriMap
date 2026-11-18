# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from salubri_api.db import get_session
from salubri_api.models import Commune, PlanVersion, Scenario, Vehicle
from salubri_api.models.audit import audit
from salubri_api.routers.deps import get_commune, parse_uuid, require_admin
from salubri_api.schemas.scenarios import BreakdownIn, RecomputeIn, ScenarioCreate, ScenarioPatch, VehicleIn
from salubri_api.services.params import PARAM_EVENT, ScenarioParams, widest_event
from salubri_api.services.plan.pipeline import latest_ready, request_recompute

router = APIRouter(prefix="/scenarios", tags=["Scénarios"], dependencies=[Depends(require_admin)])

PARAM_LABELS = {
    "population_factor": "Facteur de population",
    "waste_kg_per_person_day": "Déchets par habitant (kg/jour)",
    "subscription_rate": "Taux d'abonnement à la pré-collecte",
    "subscription_fee_fcfa_month": "Tarif d'abonnement (FCFA/mois)",
    "precollector_capacity_t": "Capacité d'un pré-collecteur (t)",
    "precollector_frequency_per_week": "Passages pré-collecte / semaine",
    "precollector_cost_fcfa_month": "Coût d'un pré-collecteur (FCFA/mois)",
    "collection_point_capacity_t": "Capacité d'un point (t)",
    "collection_point_max": "Nombre maximum de points",
    "pickup_frequency_per_week": "Enlèvements par camion / semaine",
    "walk_distance_max_m": "Distance de marche acceptable (m)",
    "season": "Saison",
    "flood_speed_factor": "Vitesse en saison des pluies (facteur)",
    "truck_breakdown_rate_per_day": "Taux de panne / jour",
    "budget_fcfa_month": "Budget mensuel (FCFA)",
    "fuel_cost_fcfa_per_km": "Ancien coût carburant (FCFA/km, remplacé par gasoil × consommation + entretien)",
    "work_start_h": "Début de journée des équipes (heure)",
    "work_end_h": "Fin de journée des équipes (heure)",
    "break_min": "Pause (minutes)",
    "work_days_per_week": "Jours travaillés par semaine",
    "fuel_price_fcfa_l": "Prix du gasoil (FCFA/litre)",
    "fuel_l_per_100km": "Consommation d'un camion (litres/100 km)",
    "maintenance_fcfa_per_km": "Entretien et pneus (FCFA/km)",
    "driver_salary_fcfa_month": "Salaire d'un chauffeur (FCFA/mois)",
    "loader_salary_fcfa_month": "Salaire d'un ripeur (FCFA/mois)",
    "loaders_per_truck": "Ripeurs par camion",
    "social_charges_rate": "Charges sociales patronales (part du salaire)",
    "truck_price_fcfa": "Prix d'un camion benne (FCFA)",
    "truck_life_years": "Durée de vie d'un camion (années)",
    "truck_insurance_fcfa_year": "Assurance et visite d'un camion (FCFA/an)",
    "bin_price_fcfa": "Prix d'un bac de regroupement (FCFA)",
    "bin_life_years": "Durée de vie d'un bac (années)",
    "cleanup_capacity_t_day": "Nettoyage des dépotoirs par la mairie (t/jour)",
    "laabal_operations_per_week": "Opérations brigade Laabal / semaine",
    "laabal_deterrence": "Effet dissuasif d'un contrôle Laabal (0-1)",
    "use_existing_cct": "Garder les CCT existants (SDGD 2020)",
    "active_quartier_ids": "Quartiers actifs",
    "horizon_days": "Horizon de simulation (jours)",
    "seed": "Graine aléatoire",
    "sim_mode": "Modèle de simulation (agents ou agrégé)",
    "vrp_time_limit_s": "Temps max. de calcul des tournées (s)",
    "placement_time_limit_s": "Temps max. de calcul du placement des points (s)",
    "placement_stability_m": "Stabilité des points : coût d'un déplacement (m de marche en plus)",
    "ilot_size_buildings": "Bâtiments par îlot",
}


def _vehicle(v: Vehicle) -> dict[str, Any]:
    return {
        "id": str(v.id),
        "label": v.label,
        "kind": v.kind,
        "capacity_t": v.capacity_t,
        "cost_per_km": v.cost_per_km,
        "fixed_cost_day": v.fixed_cost_day,
        "out_of_service": v.out_of_service,
        "shift_start": v.shift_start,
        "shift_end": v.shift_end,
    }


def scenario_out(s: Session, sc: Scenario) -> dict[str, Any]:
    ready = latest_ready(s, sc.id)
    latest = s.query(PlanVersion).filter(PlanVersion.scenario_id == sc.id).order_by(PlanVersion.version.desc()).first()
    vehicles = (
        s.query(Vehicle).filter(Vehicle.scenario_id == sc.id, Vehicle.retired.is_(False)).order_by(Vehicle.label).all()
    )
    return {
        "id": str(sc.id),
        "name": sc.name,
        "parent_id": str(sc.parent_id) if sc.parent_id else None,
        "is_baseline": sc.is_baseline,
        "params": ScenarioParams(**(sc.params or {})).model_dump(),
        "vehicles": [_vehicle(v) for v in vehicles],
        "latest_ready_plan_id": str(ready.id) if ready else None,
        "latest_plan_id": str(latest.id) if latest else None,
        "latest_plan_status": latest.status if latest else None,
        "updated_at": sc.updated_at.isoformat(),
    }


def _get(s: Session, scenario_id: str) -> Scenario:
    sc = s.get(Scenario, parse_uuid(scenario_id, "scénario"))
    if sc is None:
        raise HTTPException(404, "Scénario introuvable")
    return sc


@router.get("", summary="Lister les scénarios")
def list_scenarios(s: Session = Depends(get_session), commune: Commune = Depends(get_commune)) -> list[dict[str, Any]]:
    return [
        scenario_out(s, sc)
        for sc in s.query(Scenario)
        .filter(Scenario.commune_id == commune.id)
        .order_by(Scenario.is_baseline.desc(), Scenario.created_at)
    ]


@router.get("/params-schema", summary="Schéma des paramètres (types, bornes, libellés FR) pour générer le formulaire")
def params_schema() -> dict[str, Any]:
    schema = ScenarioParams.model_json_schema()
    for k, prop in schema.get("properties", {}).items():
        prop["label"] = PARAM_LABELS.get(k, k)
        prop["event"] = PARAM_EVENT.get(k)
    return schema


METRICS = ["points", "routes", "km_day", "cost_day_fcfa", "unserved_points", "demand_t_week"]
SIM_METRICS = [
    "collected_t",
    "wild_dump_t",
    "wild_dumps_active_final",
    "wild_dumps_active_mean",
    "overflow_point_days",
    "cost_total_fcfa",
    "cost_per_t",
    "coverage_rate",
    "subscription_rate_final",
    "mean_cleanup_delay_days",
]
BETTER_WHEN_LOWER = [
    "km_day",
    "cost_day_fcfa",
    "unserved_points",
    "sim.wild_dump_t",
    "sim.wild_dumps_active_final",
    "sim.wild_dumps_active_mean",
    "sim.overflow_point_days",
    "sim.cost_total_fcfa",
    "sim.cost_per_t",
    "sim.mean_cleanup_delay_days",
]
NEUTRAL = ["points", "routes", "demand_t_week"]


def _side(s: Session, sid: str) -> dict[str, Any]:
    sc = _get(s, sid)
    pv = latest_ready(s, sc.id)
    summ = dict(pv.summary) if pv else {}
    summ.pop("sim_daily", None)
    return {
        "scenario_id": str(sc.id),
        "name": sc.name,
        "plan_id": str(pv.id) if pv else None,
        "summary": summ,
        "wild_dumps_daily": (pv.summary.get("sim_daily", {}) if pv else {}).get("wild_dumps_active", []),
    }


def _values(summ: dict[str, Any]) -> dict[str, float]:
    out = {m: summ[m] for m in METRICS if summ.get(m) is not None}
    for m in SIM_METRICS:
        v = (summ.get("sim") or {}).get(m)
        if v is not None:
            out[f"sim.{m}"] = v
    return out


@router.get("/compare", summary="Comparer les derniers plans prêts de deux scénarios")
def compare(a: str, b: str, s: Session = Depends(get_session)) -> dict[str, Any]:
    out: dict[str, Any] = {"a": _side(s, a), "b": _side(s, b)}
    va, vb = _values(out["a"]["summary"]), _values(out["b"]["summary"])
    out["delta"] = {k: _d(va[k], vb[k]) for k in va if k in vb}
    out["better_when_lower"] = BETTER_WHEN_LOWER
    return out


@router.get("/compare-many", summary="Comparer plusieurs scénarios (le premier sert de référence)")
def compare_many(ids: str, s: Session = Depends(get_session)) -> dict[str, Any]:
    """`ids` : identifiants séparés par des virgules, 2 à 8. Pour chaque indicateur : la valeur de chaque scénario,
    l'écart à la référence et le meilleur scénario (aucun pour les indicateurs neutres ou à égalité)."""
    wanted = [x for x in dict.fromkeys(i.strip() for i in ids.split(",")) if x]
    if not 2 <= len(wanted) <= 8:
        raise HTTPException(422, "Choisir de 2 à 8 scénarios")
    sides = [_side(s, sid) for sid in wanted]
    vals = [_values(x["summary"]) for x in sides]
    keys = [k for k in vals[0] if all(k in v for v in vals)]
    rows: list[dict[str, Any]] = []
    wins = [0] * len(sides)
    for k in keys:
        series = [v[k] for v in vals]
        best: int | None = None
        if k not in NEUTRAL and len(set(series)) > 1:
            target = min(series) if k in BETTER_WHEN_LOWER else max(series)
            idx = [i for i, x in enumerate(series) if x == target]
            if len(idx) == 1:
                best = idx[0]
                wins[best] += 1
        rows.append({"key": k, "values": series, "delta": [_d(series[0], x) for x in series], "best": best})
    ranking = sorted(range(len(sides)), key=lambda i: -wins[i])
    return {
        "scenarios": sides,
        "rows": rows,
        "wins": wins,
        "ranking": [sides[i]["scenario_id"] for i in ranking],
        "better_when_lower": BETTER_WHEN_LOWER,
        "neutral": NEUTRAL,
    }


def _d(a: float, b: float) -> dict[str, float | None]:
    return {"a": a, "b": b, "value": round(b - a, 3), "pct": round((b - a) / a * 100, 1) if a else None}


@router.post("", status_code=201, summary="Créer un scénario (ou cloner depuis parent_id)")
def create_scenario(
    body: ScenarioCreate, s: Session = Depends(get_session), commune: Commune = Depends(get_commune)
) -> dict[str, Any]:
    base: dict[str, Any] = {}
    parent = None
    if body.parent_id:
        parent = _get(s, body.parent_id)
        base = dict(parent.params or {})
    try:
        params = ScenarioParams(**{**base, **body.params})
    except ValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    sc = Scenario(
        commune_id=commune.id,
        name=body.name,
        parent_id=parent.id if parent else None,
        params=params.model_dump(mode="json"),
    )
    s.add(sc)
    s.flush()
    src = (
        s.query(Vehicle).filter(Vehicle.scenario_id == parent.id, Vehicle.retired.is_(False)).all()
        if parent
        else s.query(Vehicle)
        .join(Scenario)
        .filter(Scenario.commune_id == commune.id, Scenario.is_baseline.is_(True), Vehicle.retired.is_(False))
        .all()
    )
    for v in src:
        s.add(
            Vehicle(
                scenario_id=sc.id,
                label=v.label,
                kind=v.kind,
                capacity_t=v.capacity_t,
                cost_per_km=v.cost_per_km,
                fixed_cost_day=v.fixed_cost_day,
                out_of_service=v.out_of_service,
                shift_start=v.shift_start,
                shift_end=v.shift_end,
            )
        )
    audit(s, "create", "scenario", sc.id, after={"name": sc.name, "parent": body.parent_id})
    s.commit()
    pv = request_recompute(s, sc, "manual", {"reason": "création"})
    out = scenario_out(s, sc)
    out["plan_version_id"] = str(pv.id)
    return out


@router.get("/{scenario_id}", summary="Détail d'un scénario (paramètres, camions, derniers plans)")
def get_scenario(scenario_id: str, s: Session = Depends(get_session)) -> dict[str, Any]:
    return scenario_out(s, _get(s, scenario_id))


@router.patch("/{scenario_id}", summary="Modifier des paramètres et/ou des camions : déclenche le recalcul")
def patch_scenario(scenario_id: str, body: ScenarioPatch, s: Session = Depends(get_session)) -> dict[str, Any]:
    sc = _get(s, scenario_id)
    current = ScenarioParams(**(sc.params or {}))
    try:
        new = ScenarioParams(**{**current.model_dump(), **body.params})
    except ValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    changed = {k for k in body.params if getattr(new, k, None) != getattr(current, k, None)}
    kinds = {PARAM_EVENT.get(k, "manual") for k in changed}
    if body.name:
        sc.name = body.name
    if body.vehicles is not None:
        for vin in body.vehicles:
            if vin.id:
                v = s.get(Vehicle, parse_uuid(vin.id, "camion"))
                if v is None or v.scenario_id != sc.id:
                    raise HTTPException(404, f"Camion introuvable : {vin.id}")
            else:
                v = Vehicle(
                    scenario_id=sc.id,
                    label=vin.label or "NEW",
                    kind=vin.kind or "truck_8t",
                    capacity_t=vin.capacity_t or 8,
                    cost_per_km=vin.cost_per_km or 450,
                    fixed_cost_day=vin.fixed_cost_day or 20000,
                )
                s.add(v)
            for f in ("label", "kind", "capacity_t", "cost_per_km", "fixed_cost_day", "out_of_service"):
                val = getattr(vin, f)
                if val is not None:
                    setattr(v, f, val)
        kinds.add("fleet_changed")
    sc.params = new.model_dump(mode="json")
    audit(
        s,
        "update",
        "scenario",
        sc.id,
        {"params": current.model_dump(mode="json")},
        {"changed": sorted(changed), "vehicles": body.vehicles is not None},
    )
    s.commit()
    if not kinds:
        return {"scenario": scenario_out(s, sc), "plan_version_id": None, "event": None}
    kind = widest_event(kinds)
    pv = request_recompute(s, sc, kind, {"changed": sorted(changed)})
    return {"scenario": scenario_out(s, sc), "plan_version_id": str(pv.id), "event": kind}


@router.post("/{scenario_id}/vehicles/{vehicle_id}/breakdown", summary="Raccourci « camion en panne / réparé »")
def breakdown(
    scenario_id: str, vehicle_id: str, body: BreakdownIn, s: Session = Depends(get_session)
) -> dict[str, Any]:
    sc = _get(s, scenario_id)
    v = s.get(Vehicle, parse_uuid(vehicle_id, "camion"))
    if v is None or v.scenario_id != sc.id:
        raise HTTPException(404, "Camion introuvable dans ce scénario")
    v.out_of_service = body.out_of_service
    audit(s, "breakdown" if body.out_of_service else "repair", "vehicle", v.id, after={"label": v.label})
    s.commit()
    pv = request_recompute(s, sc, "fleet_changed", {"vehicle": v.label, "out_of_service": body.out_of_service})
    return {"plan_version_id": str(pv.id), "vehicle": _vehicle(v), "event": "fleet_changed"}


VEHICLE_KINDS: dict[str, dict[str, Any]] = {
    "truck_8t": {"label": "Benne 8 t", "capacity_t": 8.0, "cost_per_km": 450.0, "fixed_cost_day": 20000.0},
    "truck_12t": {"label": "Benne 12 t", "capacity_t": 12.0, "cost_per_km": 600.0, "fixed_cost_day": 28000.0},
    "tractor_4t": {
        "label": "Tracteur-remorque 4 t",
        "capacity_t": 4.0,
        "cost_per_km": 300.0,
        "fixed_cost_day": 12000.0,
    },
}


@router.get("/meta/vehicle-kinds", summary="Types de camions proposés (capacité, coûts par défaut)")
def vehicle_kinds() -> dict[str, Any]:
    return VEHICLE_KINDS


def _next_label(s: Session, sc: Scenario) -> str:
    used = {v.label for v in s.query(Vehicle).filter(Vehicle.scenario_id == sc.id)}
    k = 1
    while f"BF-{k:02d}" in used:
        k += 1
    return f"BF-{k:02d}"


@router.post("/{scenario_id}/vehicles", status_code=201, summary="Ajouter un camion (déclenche le recalcul)")
def add_vehicle(scenario_id: str, body: VehicleIn, s: Session = Depends(get_session)) -> dict[str, Any]:
    sc = _get(s, scenario_id)
    kind = body.kind or "truck_8t"
    base = VEHICLE_KINDS.get(kind, VEHICLE_KINDS["truck_8t"])
    v = Vehicle(
        scenario_id=sc.id,
        label=(body.label or _next_label(s, sc))[:32],
        kind=kind[:16],
        capacity_t=body.capacity_t or base["capacity_t"],
        cost_per_km=body.cost_per_km if body.cost_per_km is not None else base["cost_per_km"],
        fixed_cost_day=body.fixed_cost_day if body.fixed_cost_day is not None else base["fixed_cost_day"],
        out_of_service=False,
    )
    s.add(v)
    s.flush()
    audit(s, "create", "vehicle", v.id, after={"label": v.label, "kind": v.kind})
    s.commit()
    pv = request_recompute(s, sc, "fleet_changed", {"vehicle": v.label, "added": True})
    return {"plan_version_id": str(pv.id), "vehicle": _vehicle(v), "event": "fleet_changed"}


@router.delete("/{scenario_id}/vehicles/{vehicle_id}", summary="Retirer un camion de la flotte (historique conservé)")
def remove_vehicle(scenario_id: str, vehicle_id: str, s: Session = Depends(get_session)) -> dict[str, Any]:
    sc = _get(s, scenario_id)
    v = s.get(Vehicle, parse_uuid(vehicle_id, "camion"))
    if v is None or v.scenario_id != sc.id or v.retired:
        raise HTTPException(404, "Camion introuvable dans ce scénario")
    remaining = (
        s.query(Vehicle).filter(Vehicle.scenario_id == sc.id, Vehicle.retired.is_(False), Vehicle.id != v.id).count()
    )
    if remaining == 0:
        raise HTTPException(409, "Impossible de retirer le dernier camion du scénario")
    v.retired = True
    audit(s, "delete", "vehicle", v.id, before={"label": v.label})
    s.commit()
    pv = request_recompute(s, sc, "fleet_changed", {"vehicle": v.label, "removed": True})
    return {"plan_version_id": str(pv.id), "event": "fleet_changed"}


@router.post("/{scenario_id}/recompute", summary="Recalcul complet manuel")
def recompute(scenario_id: str, body: RecomputeIn | None = None, s: Session = Depends(get_session)) -> dict[str, Any]:
    sc = _get(s, scenario_id)
    pv = request_recompute(s, sc, "manual", {"reason": body.reason if body else None})
    return {"plan_version_id": str(pv.id), "event": "manual"}


@router.delete("/{scenario_id}", status_code=204, summary="Supprimer un scénario (sauf le scénario de base)")
def delete_scenario(scenario_id: str, s: Session = Depends(get_session)) -> None:
    sc = _get(s, scenario_id)
    if sc.is_baseline:
        raise HTTPException(409, "Le scénario de base ne peut pas être supprimé")
    s.delete(sc)
    s.commit()
