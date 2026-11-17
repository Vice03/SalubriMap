# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from salubri_api.db import get_session, get_sessionmaker
from salubri_api.models import CollectionPoint, PlanVersion, Route, RouteStop, SimRun, UnservedPoint, Vehicle
from salubri_api.routers.deps import parse_uuid, require_admin
from salubri_api.schemas.plans import SimulateIn
from salubri_api.services import background
from salubri_api.services.geo import feature, feature_collection
from salubri_api.services.params import ScenarioParams
from salubri_api.services.plan import bus
from salubri_api.services.plan.diff import diff_plans
from salubri_api.services.plan.pipeline import latest_ready, plan_view, snapshot_from_db
from salubri_api.services.simulation.engine import replicate
from salubri_api.services.simulation.params import SimParams

router = APIRouter(prefix="/plans", tags=["Plans"], dependencies=[Depends(require_admin)])


def _get(s: Session, plan_id: str) -> PlanVersion:
    pv = s.get(PlanVersion, parse_uuid(plan_id, "plan"))
    if pv is None:
        raise HTTPException(404, "Version de plan introuvable")
    return pv


def plan_out(pv: PlanVersion, include_daily: bool = False) -> dict[str, Any]:
    summ = dict(pv.summary or {})
    if not include_daily:
        summ.pop("sim_daily", None)
    return {
        "id": str(pv.id),
        "scenario_id": str(pv.scenario_id),
        "version": pv.version,
        "status": pv.status,
        "event": pv.event_kind,
        "distance_mode": pv.distance_mode,
        "stages": pv.stages,
        "summary": summ,
        "error": pv.error,
        "created_at": pv.created_at.isoformat(),
        "started_at": pv.started_at.isoformat() if pv.started_at else None,
        "finished_at": pv.finished_at.isoformat() if pv.finished_at else None,
    }


@router.get("/{plan_id}", summary="Statut, étapes et résumé d'une version de plan")
def get_plan(plan_id: str, daily: bool = False, s: Session = Depends(get_session)) -> dict[str, Any]:
    return plan_out(_get(s, plan_id), daily)


@router.get(
    "/{plan_id}/events",
    summary="Progression en direct (Server-Sent Events)",
    description="Événements : running, stage_started, stage_done, ready, failed, superseded.",
)
async def plan_events(plan_id: str, request: Request) -> EventSourceResponse:
    pid = str(parse_uuid(plan_id, "plan"))

    async def gen() -> AsyncIterator[dict[str, str]]:
        offset = 0
        for _ in range(1200):  # 2 minutes max
            if await request.is_disconnected():
                return
            events = bus.read_from(pid, offset)
            offset += len(events)
            for e in events:
                yield {"event": e["event"], "data": json.dumps(e["data"], default=str)}
                if e["event"] in ("ready", "failed", "superseded"):
                    return
            if not events and offset == 0:
                with get_sessionmaker()() as s:  # restarted server or finished long ago: replay from the database
                    pv = s.get(PlanVersion, parse_uuid(pid))
                    if pv is not None and pv.status in ("ready", "failed", "superseded"):
                        for st in pv.stages or []:
                            yield {"event": "stage_done", "data": json.dumps(st)}
                        data = (
                            {"version": pv.version, "error": pv.error}
                            if pv.status != "ready"
                            else {
                                "version": pv.version,
                                "summary": {k: v for k, v in (pv.summary or {}).items() if k != "sim_daily"},
                            }
                        )
                        yield {"event": pv.status, "data": json.dumps(data, default=str)}
                        return
            await asyncio.sleep(0.1)

    return EventSourceResponse(gen(), ping=5)


@router.get("/{plan_id}/points", summary="Points de regroupement (FeatureCollection)")
def points(plan_id: str, s: Session = Depends(get_session)) -> dict[str, Any]:
    pv = _get(s, plan_id)
    unserved = {u.collection_point_id for u in s.query(UnservedPoint).filter(UnservedPoint.plan_version_id == pv.id)}
    rows = s.query(CollectionPoint).filter(CollectionPoint.plan_version_id == pv.id).order_by(CollectionPoint.idx).all()
    per_week = float((pv.params_snapshot or {}).get("pickup_frequency_per_week", 2)) or 1.0
    return feature_collection(
        [
            feature(
                p.geom,
                {
                    "id": str(p.id),
                    "key": p.key,
                    "label": p.label,
                    "capacity_t": p.capacity_t,
                    "demand_t_week": p.demand_t_week,
                    "fill_ratio_per_pickup": round(p.demand_t_week / per_week / p.capacity_t, 3)
                    if p.capacity_t
                    else None,
                    "n_ilots": len(p.ilot_ids),
                    "frozen": p.frozen,
                    "time_window": [p.tw_start, p.tw_end],
                    "unserved": p.id in unserved,
                },
                p.id,
            )
            for p in rows
        ]
    )


@router.get("/{plan_id}/routes", summary="Tournées (FeatureCollection de LineString, avec arrêts et horaires)")
def routes(plan_id: str, s: Session = Depends(get_session)) -> dict[str, Any]:
    pv = _get(s, plan_id)
    key_of = {p.id: p.key for p in s.query(CollectionPoint).filter(CollectionPoint.plan_version_id == pv.id)}
    rows = s.query(Route).filter(Route.plan_version_id == pv.id).all()
    vehicles = {v.id: v for v in s.query(Vehicle).filter(Vehicle.id.in_([r.vehicle_id for r in rows]))} if rows else {}
    feats = []
    for r in sorted(rows, key=lambda r: (vehicles[r.vehicle_id].label, r.rotation)):
        stops = s.query(RouteStop).filter(RouteStop.route_id == r.id).order_by(RouteStop.seq).all()
        v = vehicles[r.vehicle_id]
        feats.append(
            feature(
                r.geom,
                {
                    "id": str(r.id),
                    "vehicle_id": str(v.id),
                    "vehicle_label": v.label,
                    "vehicle_kind": v.kind,
                    "capacity_t": v.capacity_t,
                    "rotation": r.rotation,
                    "distance_km": r.distance_km,
                    "duration_min": r.duration_min,
                    "load_t": r.load_t,
                    "cost_fcfa": r.cost,
                    "stops": [
                        {
                            "seq": x.seq,
                            "point_key": key_of.get(x.collection_point_id),
                            "point_id": str(x.collection_point_id),
                            "arrival_min": x.arrival_min,
                            "load_t_after": x.load_t_after,
                        }
                        for x in stops
                    ],
                },
                r.id,
            )
        )
    return feature_collection(feats)


@router.get("/{plan_id}/unserved", summary="Points non desservis")
def unserved(plan_id: str, s: Session = Depends(get_session)) -> list[dict[str, Any]]:
    pv = _get(s, plan_id)
    out = []
    for u in s.query(UnservedPoint).filter(UnservedPoint.plan_version_id == pv.id):
        cp = s.get(CollectionPoint, u.collection_point_id)
        out.append(
            {
                "point_id": str(u.collection_point_id),
                "point_key": cp.key if cp else None,
                "demand_t_week": u.demand_t_week,
                "reason": u.reason,
            }
        )
    return out


@router.get("/{plan_id}/diff", summary="Différences avec une autre version (par défaut : la précédente prête)")
def diff(plan_id: str, against: str | None = None, s: Session = Depends(get_session)) -> dict[str, Any]:
    pv = _get(s, plan_id)
    other = _get(s, against) if against else latest_ready(s, pv.scenario_id, pv.version)
    return {
        "plan_id": str(pv.id),
        "against": str(other.id) if other else None,
        **diff_plans(plan_view(s, other) if other else None, plan_view(s, pv)),
    }


def _run_replications(run_id: str, plan_id: str, seed: int, horizon: int | None, n: int, mode: str | None) -> None:
    with get_sessionmaker()() as s:
        run = s.get(SimRun, parse_uuid(run_id))
        pv = s.get(PlanVersion, parse_uuid(plan_id))
        assert run is not None and pv is not None
        try:
            run.status = "running"
            s.commit()
            params = ScenarioParams(**(pv.params_snapshot or {}))
            if horizon:
                params = params.model_copy(update={"horizon_days": horizon})
            res = replicate(snapshot_from_db(s, pv), SimParams.from_scenario(params), seed, n, mode or params.sim_mode)
            run.metrics_summary, run.metrics_daily = res["summary"], res["daily"]  # type: ignore[assignment]
            run.duration_ms, run.status = int(res["duration_ms"]), "ready"  # type: ignore[call-overload]
        except Exception as exc:
            run.status, run.error = "failed", str(exc)
        s.commit()


@router.post("/{plan_id}/simulate", status_code=202, summary="Lancer des réplications de la simulation (arrière-plan)")
def simulate_plan(plan_id: str, body: SimulateIn, s: Session = Depends(get_session)) -> dict[str, Any]:
    pv = _get(s, plan_id)
    if pv.status != "ready":
        raise HTTPException(409, "Le plan n'est pas prêt")
    seed = body.seed if body.seed is not None else int((pv.params_snapshot or {}).get("seed", 42))
    horizon = body.horizon_days or int((pv.params_snapshot or {}).get("horizon_days", 90))
    run = SimRun(plan_version_id=pv.id, seed=seed, horizon_days=horizon, replications=body.replications)
    s.add(run)
    s.commit()
    background.spawn(
        _run_replications, str(run.id), str(pv.id), seed, body.horizon_days, body.replications, body.mode, name="sim"
    )
    return {"sim_run_id": str(run.id), "status": "pending"}
