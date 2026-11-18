# SPDX-License-Identifier: AGPL-3.0-or-later
"""Event-driven recompute pipeline E1..E7 with per-stage cache, immutable plan versions and SSE progress.

Guarantees:
- a recompute always creates a NEW plan_versions row; the previous `ready` one keeps being served until the
  new one is ready (never an intermediate state);
- one pipeline at a time per scenario; events arriving meanwhile are merged into a single follow-up run
  (older pending versions become `superseded`);
- a failure marks the version `failed` and leaves the previous ready version in place.
"""

import hashlib
import json
import logging
import math
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from shapely.geometry import LineString, Point
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from salubri_api.config import get_settings
from salubri_api.db import get_sessionmaker
from salubri_api.models import (
    CollectionPoint,
    Commune,
    PlanEvent,
    PlanVersion,
    Route,
    RouteStop,
    Scenario,
    UnservedPoint,
    Vehicle,
    utcnow,
)
from salubri_api.services import background, costs
from salubri_api.services.consolidation import consolidate
from salubri_api.services.demand import demand_kg_day
from salubri_api.services.geo import haversine_m, shape, to_wkb
from salubri_api.services.params import ScenarioParams, widest_event
from salubri_api.services.plan import bus
from salubri_api.services.plan.diff import PlanView, diff_plans
from salubri_api.services.plan.events import INCREMENTAL_POINTS, INVALIDATES, STAGES
from salubri_api.services.planning.collection_points import (
    PlacedPoint,
    PlacementResult,
    effective_frequency,
    place_points,
)
from salubri_api.services.planning.distance import Matrix, build_matrix, route_geometry
from salubri_api.services.planning.vrp import VehicleSpec, VrpSolution, lower_bound_km, solve_vrp
from salubri_api.services.reference import existing_cct
from salubri_api.services.simulation.agents import PlanSnapshot, TruckRoute
from salubri_api.services.simulation.engine import SimResult
from salubri_api.services.simulation.engine import run as run_sim
from salubri_api.services.simulation.params import SimParams

log = logging.getLogger("salubri.pipeline")
STAGE_NAMES = {code: label for code, _, label in STAGES}
MARKET_TW = (300, 480)
DEFAULT_TW = (420, 1020)
SERVICE_MIN = 10


def _h(*parts: Any) -> str:
    return hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:16]


@dataclass
class Cached:
    key: str
    output: Any


@dataclass
class Ilots:
    ids: list[uuid.UUID]
    lonlat: np.ndarray
    population: np.ndarray
    near_water: np.ndarray
    demand_kg_day: np.ndarray
    sig: str


@dataclass
class Points:
    placement: PlacementResult
    time_windows: list[tuple[int, int]]


@dataclass
class Vrp:
    solution: VrpSolution
    vehicles: list[Vehicle]
    loads_t: np.ndarray
    geometries: list[list[tuple[float, float]]]


@dataclass
class RunState:
    stages: list[dict[str, Any]] = field(default_factory=list)


# sorties des étapes, par scénario ; seuls les MAX_CACHED_SCENARIOS derniers recalculés sont gardés (mémoire :
# la ville entière garde ~100 Mo d'étapes, et chaque cas simulé de la page Comparer est un scénario)
_cache: "OrderedDict[str, dict[str, Cached]]" = OrderedDict()
MAX_CACHED_SCENARIOS = 6
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(scenario_id: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(scenario_id, threading.Lock())


def reset_cache() -> None:
    _cache.clear()


# ---------------------------------------------------------------- spatial callables for placement
def _project_fn(s: Session, commune_id: uuid.UUID):  # type: ignore[no-untyped-def]
    n_roads = s.execute(
        text("SELECT count(*) FROM roads WHERE commune_id = :c AND truck_ok"), {"c": commune_id}
    ).scalar_one()
    if not n_roads:
        return None

    def project(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
        rows = s.execute(
            text("""
            SELECT u.i, ST_X(cp) AS lon, ST_Y(cp) AS lat FROM unnest(CAST(:lons AS float8[]), CAST(:lats AS float8[]))
              WITH ORDINALITY AS u(lon, lat, i)
            CROSS JOIN LATERAL (
              SELECT ST_ClosestPoint(r.geom, ST_SetSRID(ST_MakePoint(u.lon, u.lat), 4326)) AS cp
              FROM roads r WHERE r.commune_id = :c AND r.truck_ok
              ORDER BY r.geom <-> ST_SetSRID(ST_MakePoint(u.lon, u.lat), 4326) LIMIT 1) q
            ORDER BY u.i"""),
            {"lons": [p[0] for p in pts], "lats": [p[1] for p in pts], "c": commune_id},
        ).all()
        return [(float(r.lon), float(r.lat)) for r in rows]

    return project


def _candidates_fn(s: Session, commune_id: uuid.UUID):  # type: ignore[no-untyped-def]
    """Sites candidats : points des routes praticables tous les ~50 m dans l'emprise, au plus ~2500 (grille plus
    lâche au-delà), pour le placement CP-SAT."""

    def candidates(bbox: tuple[float, float, float, float]) -> list[tuple[float, float]]:
        for cell in (0.00045, 0.0009, 0.0018, 0.0036):  # ~50, 100, 200, 400 m
            rows = s.execute(
                text("""
                WITH env AS (SELECT ST_MakeEnvelope(:x0, :y0, :x1, :y1, 4326) AS g),
                pts AS (
                  SELECT (ST_DumpPoints(ST_Segmentize(ST_Intersection(r.geom, env.g)::geography, 50)::geometry)).geom AS g
                  FROM roads r, env WHERE r.commune_id = :c AND r.truck_ok AND r.geom && env.g)
                SELECT DISTINCT ON (ST_SnapToGrid(g, :cell)) ST_X(g) AS lon, ST_Y(g) AS lat FROM pts
                WHERE GeometryType(g) = 'POINT' LIMIT 2501"""),
                {"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3], "c": commune_id, "cell": cell},
            ).all()
            if len(rows) <= 2500:
                return [(float(r.lon), float(r.lat)) for r in rows]
        return [(float(r.lon), float(r.lat)) for r in rows[:2500]]

    return candidates


def _excluded_fn(s: Session, commune_id: uuid.UUID):  # type: ignore[no-untyped-def]
    def excluded(pts: list[tuple[float, float]]) -> list[bool]:
        rows = s.execute(
            text("""
            WITH u AS (SELECT i, ST_SetSRID(ST_MakePoint(lon, lat), 4326) AS g
                       FROM unnest(CAST(:lons AS float8[]), CAST(:lats AS float8[])) WITH ORDINALITY AS t(lon, lat, i))
            SELECT u.i,
              EXISTS (SELECT 1 FROM buildings b WHERE b.commune_id = :c AND b.confidence >= 0.7
                      AND ST_Contains(b.geom, u.g))
              OR EXISTS (SELECT 1 FROM water w WHERE w.commune_id = :c AND ST_DWithin(w.geom, u.g, 0.001)
                      AND ST_DWithin(w.geom::geography, u.g::geography, 15))
              OR EXISTS (SELECT 1 FROM pois p WHERE p.commune_id = :c
                      AND p.kind IN ('school','marketplace','cemetery','military')
                      AND ST_DWithin(p.geom, u.g, 0.002) AND ST_DWithin(p.geom::geography, u.g::geography, 50)) AS bad
            FROM u ORDER BY u.i"""),
            {"lons": [p[0] for p in pts], "lats": [p[1] for p in pts], "c": commune_id},
        ).all()
        return [bool(r.bad) for r in rows]

    return excluded


def _time_windows(s: Session, commune_id: uuid.UUID, pts: list[PlacedPoint]) -> list[tuple[int, int]]:
    if not pts:
        return []
    rows = s.execute(
        text("""
        SELECT EXISTS (SELECT 1 FROM pois p WHERE p.commune_id = :c AND p.kind = 'marketplace'
               AND ST_DWithin(p.geom::geography, ST_SetSRID(ST_MakePoint(u.lon, u.lat), 4326)::geography, 150)) AS m
        FROM unnest(CAST(:lons AS float8[]), CAST(:lats AS float8[])) WITH ORDINALITY AS u(lon, lat, i) ORDER BY u.i"""),
        {"lons": [p.lon for p in pts], "lats": [p.lat for p in pts], "c": commune_id},
    ).all()
    return [MARKET_TW if r.m else DEFAULT_TW for r in rows]


# ---------------------------------------------------------------- public entry points
def _trucks_needed(demand_nodes: np.ndarray, unserved: list[int], vehicles: list[Any]) -> int | None:
    """Ordre de grandeur de la flotte nécessaire quand des points restent non desservis.

    Camions × (tonnage total / tonnage réellement servi par la flotte actuelle), borné en dessous par la
    capacité (2 rotations par camion). None quand tout est desservi.
    """
    if not unserved or not vehicles:
        return None
    total = float(demand_nodes.sum())
    served = total - float(sum(demand_nodes[i] for i in unserved))
    cap = float(np.mean([v.capacity_t for v in vehicles])) * 2
    by_capacity = math.ceil(total / cap) if cap > 0 else len(vehicles)
    by_observed = math.ceil(len(vehicles) * total / served) if served > 0 else by_capacity
    return max(len(vehicles) + 1, by_capacity, by_observed)


def request_recompute(
    s: Session, scenario: Scenario, kind: str, payload: dict[str, Any] | None = None, sync: bool = False
) -> PlanVersion:
    ev = PlanEvent(scenario_id=scenario.id, kind=kind, payload=payload or {})
    s.add(ev)
    s.flush()
    last = s.query(func.max(PlanVersion.version)).filter(PlanVersion.scenario_id == scenario.id).scalar() or 0
    pv = PlanVersion(
        scenario_id=scenario.id,
        event_id=ev.id,
        event_kind=kind,
        version=last + 1,
        status="pending",
        params_snapshot=scenario.params,
    )
    s.add(pv)
    s.commit()
    if sync:
        run_pending(str(scenario.id))
        s.refresh(pv)
    else:
        background.spawn(run_pending, str(scenario.id), name=f"plan-{scenario.id}")
    return pv


def run_pending(scenario_id: str) -> None:
    lock = _lock_for(scenario_id)
    while True:
        if not lock.acquire(blocking=False):
            return  # the running worker picks pending versions up when it finishes
        try:
            while True:
                with get_sessionmaker()() as s:
                    pending = (
                        s.query(PlanVersion)
                        .filter(PlanVersion.scenario_id == uuid.UUID(scenario_id), PlanVersion.status == "pending")
                        .order_by(PlanVersion.version)
                        .all()
                    )
                    if not pending:
                        break
                    latest = pending[-1]
                    kind = widest_event({p.event_kind for p in pending})
                    for older in pending[:-1]:
                        older.status = "superseded"
                        older.error = f"Remplacée par la version {latest.version}"
                        older.finished_at = utcnow()
                        bus.publish(str(older.id), "superseded", {"by": str(latest.id), "version": latest.version})
                    latest.event_kind = kind
                    s.commit()
                    target = str(latest.id)
                _execute(target)
        finally:
            lock.release()
        with get_sessionmaker()() as s:
            if (
                not s.query(PlanVersion)
                .filter(PlanVersion.scenario_id == uuid.UUID(scenario_id), PlanVersion.status == "pending")
                .count()
            ):
                return


# ---------------------------------------------------------------- execution
def _stage(pv_id: str, st: RunState, cache: dict[str, Cached], code: str, key: str, forced: bool, fn):  # type: ignore[no-untyped-def]
    hit = (not forced) and code in cache and cache[code].key == key
    bus.publish(pv_id, "stage_started", {"stage": code, "name": STAGE_NAMES[code]})
    t0 = time.perf_counter()
    if hit:
        out = cache[code].output
    else:
        out = fn()
        cache[code] = Cached(key, out)
    ms = int((time.perf_counter() - t0) * 1000)
    rec = {"stage": code, "name": STAGE_NAMES[code], "duration_ms": ms, "cache_hit": hit}
    st.stages.append(rec)
    bus.publish(pv_id, "stage_done", rec)
    log.info(json.dumps({"plan": pv_id, **rec}))
    return out


def latest_ready(s: Session, scenario_id: uuid.UUID, before_version: int | None = None) -> PlanVersion | None:
    q = s.query(PlanVersion).filter(PlanVersion.scenario_id == scenario_id, PlanVersion.status == "ready")
    if before_version is not None:
        q = q.filter(PlanVersion.version < before_version)
    return q.order_by(PlanVersion.version.desc()).first()


def plan_view(s: Session, pv: PlanVersion) -> PlanView:
    pts = s.query(CollectionPoint).filter(CollectionPoint.plan_version_id == pv.id).all()
    key_of = {p.id: p.key for p in pts}
    routes = s.query(Route).filter(Route.plan_version_id == pv.id).all()
    vlabel = (
        {v.id: v.label for v in s.query(Vehicle).filter(Vehicle.id.in_([r.vehicle_id for r in routes]))}
        if routes
        else {}
    )
    rset = set()
    for r in routes:
        stops = s.query(RouteStop).filter(RouteStop.route_id == r.id).order_by(RouteStop.seq).all()
        rset.add((vlabel.get(r.vehicle_id, "?"), r.rotation, tuple(key_of[x.collection_point_id] for x in stops)))
    return PlanView(
        points={p.key: (shape(p.geom).x, shape(p.geom).y) for p in pts},
        routes=rset,
        km=float(sum(r.distance_km for r in routes)),
        cost=float(sum(r.cost for r in routes)),
        unserved=s.query(UnservedPoint).filter(UnservedPoint.plan_version_id == pv.id).count(),
        coverage=(pv.summary or {}).get("coverage_walk"),
    )


def _execute(pv_id: str) -> None:
    settings = get_settings()
    with get_sessionmaker()() as s:
        pv = s.get(PlanVersion, uuid.UUID(pv_id))
        if pv is None:
            return
        pv.status, pv.started_at = "running", utcnow()
        s.commit()
        bus.publish(pv_id, "running", {"version": pv.version, "event": pv.event_kind})
        try:
            scenario = s.get(Scenario, pv.scenario_id)
            assert scenario is not None
            commune = s.get(Commune, scenario.commune_id)
            assert commune is not None
            params = ScenarioParams(**(scenario.params or {}))
            pv.params_snapshot = params.model_dump()
            kind = pv.event_kind
            must = INVALIDATES.get(kind, INVALIDATES["manual"])
            forced_all = kind == "manual"
            cache = _cache.setdefault(str(scenario.id), {})
            _cache.move_to_end(str(scenario.id))
            while len(_cache) > MAX_CACHED_SCENARIOS:
                _cache.popitem(last=False)
            prev = latest_ready(s, scenario.id, pv.version)
            st = RunState()
            seasons = None
            if settings.seasons_enabled:  # module « Saisons » (docs/MODULES.md) : état des routes de la période
                from salubri_api.modules.seasons import service as seasons

                seasons.activate(seasons.load_context(s, commune.id, params.season))

            # E1 consolidation (database side effect, keyed on the verified-report signature)
            sig = s.execute(
                text("""SELECT
                  (SELECT count(*) FROM reports WHERE commune_id = :c AND status IN ('verified','cleaned')),
                  (SELECT md5(coalesce(string_agg(id::text || status || ST_AsText(geom), ',' ORDER BY id), ''))
                     FROM reports WHERE commune_id = :c AND status IN ('verified','cleaned')),
                  (SELECT md5(coalesce(string_agg(id::text || status || coalesce(cleaned_at::text, ''), ',' ORDER BY id), ''))
                     FROM dump_sites WHERE commune_id = :c)"""),
                {"c": commune.id},
            ).one()
            e1 = _stage(
                pv_id,
                st,
                cache,
                "E1",
                _h(list(sig)),
                forced_all or "E1" in must and kind == "reports_changed",
                lambda: {"result": consolidate(s, commune.id), "dump_sites": None},
            )
            s.commit()

            # E2 ilots and demand
            q_ids = params.active_quartier_ids
            rows = s.execute(
                text("""
                SELECT i.id, ST_X(i.centroid) AS lon, ST_Y(i.centroid) AS lat, i.population, i.near_water
                FROM ilots i JOIN quartiers q ON q.id = i.quartier_id
                WHERE q.commune_id = :c AND q.active AND (CAST(:ids AS uuid[]) IS NULL OR q.id = ANY(CAST(:ids AS uuid[])))
                ORDER BY i.id"""),
                {"c": commune.id, "ids": q_ids},
            ).all()
            ilot_sig = _h([str(r.id) for r in rows], round(sum(r.population for r in rows), 1))

            def run_e2() -> Ilots:
                pop = np.array([r.population for r in rows], dtype=float)
                return Ilots(
                    ids=[r.id for r in rows],
                    lonlat=np.array([[r.lon, r.lat] for r in rows], dtype=float),
                    population=pop,
                    near_water=np.array([bool(r.near_water) for r in rows]),
                    demand_kg_day=demand_kg_day(pop, params),
                    sig=ilot_sig,
                )

            e2_key = _h(ilot_sig, params.population_factor, params.waste_kg_per_person_day, params.season)
            ilots: Ilots = _stage(pv_id, st, cache, "E2", e2_key, forced_all, run_e2)
            if len(ilots.ids) == 0:
                raise RuntimeError("Aucun îlot dans les quartiers actifs : lancer le seed ou activer des quartiers")

            # E3 collection points
            incremental = kind in INCREMENTAL_POINTS and prev is not None
            frozen: list[PlacedPoint] = []
            if incremental and prev is not None:
                for cp in (
                    s.query(CollectionPoint)
                    .filter(CollectionPoint.plan_version_id == prev.id)
                    .order_by(CollectionPoint.idx)
                ):
                    g = shape(cp.geom)
                    if _serves_area(ilots.lonlat, g.x, g.y, params.walk_distance_max_m):
                        frozen.append(PlacedPoint(cp.key, g.x, g.y, cp.capacity_t, frozen=True))
            previous: list[
                PlacedPoint
            ] = []  # placement complet : points d'avant, déplacés seulement si ça vaut le coût
            if not incremental and prev is not None:
                for cp in s.query(CollectionPoint).filter(CollectionPoint.plan_version_id == prev.id):
                    g = shape(cp.geom)
                    if _serves_area(ilots.lonlat, g.x, g.y, params.walk_distance_max_m):
                        previous.append(PlacedPoint(cp.key, g.x, g.y, cp.capacity_t))
            if params.use_existing_cct:
                # CCT existants (SDGD 2020) qui desservent la zone active : gardés tels quels
                have = {f.key for f in frozen}
                il = ilots.lonlat
                for key, lon, lat in existing_cct(commune.slug):
                    if key in have or not len(il):
                        continue
                    d = np.hypot((il[:, 0] - lon) * 108_700, (il[:, 1] - lat) * 110_600).min()
                    if d <= params.walk_distance_max_m:
                        frozen.append(PlacedPoint(key, lon, lat, params.collection_point_capacity_t, frozen=True))
            e3_structural = _h(
                ilots.sig,
                params.collection_point_capacity_t,
                params.collection_point_max,
                params.pickup_frequency_per_week,
                params.walk_distance_max_m,
                params.seed,
                params.population_factor,
                params.waste_kg_per_person_day,
                [f.key for f in frozen] if (incremental or params.use_existing_cct) else None,
                params.placement_time_limit_s,
                params.placement_stability_m,
            )
            if seasons is not None:  # routes impraticables : le placement complet en tient compte
                e3_structural = _h(e3_structural, seasons.current().signature)
            e3_forced = forced_all or ("E3" in must and kind != "season_changed")
            cached_e3 = cache.get("E3")
            if (
                not e3_forced
                and cached_e3 is not None
                and cached_e3.output.placement.points
                and getattr(cached_e3.output, "ilot_sig", None) == ilots.sig
            ):
                e3_key = cached_e3.key  # same ilots: keep the points where they are
            else:
                e3_key = e3_structural

            def run_e3() -> Points:
                res = place_points(
                    ilots.lonlat,
                    ilots.demand_kg_day,
                    params,
                    project=_project_fn(s, commune.id),
                    excluded=_excluded_fn(s, commune.id),
                    frozen=frozen or None,
                    seed=params.seed,
                    candidates=_candidates_fn(s, commune.id) if _project_fn(s, commune.id) is not None else None,
                    previous=previous,
                )
                pts = Points(res, _time_windows(s, commune.id, res.points))
                pts.ilot_sig = ilots.sig  # type: ignore[attr-defined]
                return pts

            points: Points = _stage(pv_id, st, cache, "E3", e3_key, e3_forced, run_e3)
            placement = points.placement
            # point loads always follow the current demand (season, population) even when positions are reused
            w_week = ilots.demand_kg_day * 7 / 1000
            loads_week = np.bincount(placement.assignment, weights=w_week, minlength=len(placement.points))
            for i, p in enumerate(placement.points):
                p.demand_t_week = float(loads_week[i])
            variant = None
            if seasons is not None:  # points dont la route d'accès est impraticable : déplacés ou signalés
                placement, variant = seasons.seasonal_variant(
                    s, placement, ilots.lonlat, ilots.population * params.population_factor,
                    _candidates_fn(s, commune.id), params.walk_distance_max_m,
                )  # fmt: skip
            # Capacité par enlèvement (contrainte dure) : fréquence la plus basse où chaque point tient dans son bac
            # avec la demande du moment (saison, population), au plus `pickup_frequency_max_per_week` ; les points
            # qui débordent encore sont listés, jamais tronqués en silence.
            caps = np.array([p.capacity_t for p in placement.points])
            f_base = float((placement.optimisation or {}).get("capacite", {}).get("enlevements_semaine")
                           or params.pickup_frequency_per_week)  # fmt: skip
            f_eff, over_idx = effective_frequency(
                loads_week,
                caps,
                max(f_base, params.pickup_frequency_per_week),
                min(
                    params.pickup_frequency_max_per_week, params.work_days_per_week
                ),  # jamais plus que les jours travaillés
            )
            capacite = {
                "enlevements_semaine_demandes": params.pickup_frequency_per_week,
                "enlevements_semaine": f_eff,
                "respectee": not over_idx,
                "points_debordants": [
                    {
                        "point": placement.points[i].key,
                        "demande_par_enlevement_t": round(float(loads_week[i] / f_eff), 2),
                        "capacite_t": float(caps[i]),
                    }
                    for i in over_idx
                ],  # fmt: skip
                "non_collecte_t_semaine": round(float(np.maximum(loads_week - caps * f_eff, 0).sum()), 2),
            }
            if f_eff != params.pickup_frequency_per_week:
                params = params.model_copy(update={"pickup_frequency_per_week": f_eff})
                pv.params_snapshot = params.model_dump()  # paramètres effectivement utilisés (summary.capacite)

            # E4 distance matrix
            depot = shape(commune.depot_geom)
            nodes = [(depot.x, depot.y)] + [(p.lon, p.lat) for p in placement.points]
            url = settings.osrm_rain_url if params.season == "rain" else settings.osrm_url
            detour = params.fallback_detour_rain if params.season == "rain" else params.fallback_detour_dry
            e4_key = _h(nodes, params.season, url, params.flood_speed_factor, detour)
            matrix: Matrix = _stage(
                pv_id,
                st,
                cache,
                "E4",
                e4_key,
                forced_all,
                lambda: build_matrix(
                    nodes, params.season, url or None, settings.osrm_timeout_s, params.flood_speed_factor, detour
                ),
            )

            if seasons is not None and variant is not None:  # arcs coupés hors de prix, points inaccessibles abandonnés
                inacc = {k + 1 for k, q in enumerate(placement.points)
                         if q.key in {x["point"] for x in variant.inaccessible}}  # fmt: skip
                matrix = seasons.penalise_matrix(matrix, nodes, inacc)
                e4_key = _h(e4_key, seasons.current().signature, sorted(inacc))
            # E5 vehicle routing
            vehicles = (
                s.query(Vehicle)
                .filter(
                    Vehicle.scenario_id == scenario.id, Vehicle.out_of_service.is_(False), Vehicle.retired.is_(False)
                )
                .order_by(Vehicle.label)
                .all()
            )
            per_pickup = np.minimum(
                loads_week / params.pickup_frequency_per_week, np.array([p.capacity_t for p in placement.points])
            )
            demand_nodes = np.concatenate([[0.0], per_pickup])
            tws = [(0, 1440)] + points.time_windows
            shift = params.shift_minutes  # horaires des équipes (réglables) : 8 h – 18 h, pause déduite par défaut
            specs = [VehicleSpec(v.capacity_t, v.cost_per_km, v.fixed_cost_day, *shift, v.label) for v in vehicles]
            e5_key = _h(
                e4_key,
                np.round(demand_nodes, 3).tolist(),
                [(v.label, v.capacity_t, v.cost_per_km) for v in vehicles],
                shift,
                params.vrp_time_limit_s,
                tws,
            )

            def run_e5() -> Vrp:
                sol = solve_vrp(
                    matrix.distance_km,
                    matrix.duration_min,
                    demand_nodes,
                    specs,
                    tws,
                    SERVICE_MIN,
                    time_limit_s=params.vrp_time_limit_s,
                )
                geoms = []
                for r in sol.routes:
                    seq = [nodes[0]] + [nodes[i] for i in r.stops] + [nodes[0]]
                    geoms.append(
                        route_geometry(seq, url or None, settings.osrm_timeout_s) if matrix.mode == "osrm" else seq
                    )
                return Vrp(sol, vehicles, per_pickup, geoms)

            vrp: Vrp = _stage(pv_id, st, cache, "E5", e5_key, forced_all, run_e5)
            vrp.vehicles = vehicles  # rows of this session

            # E6 quick simulation
            sp = SimParams.from_scenario(params)
            snap = _snapshot(ilots, placement, vrp, params)
            if seasons is not None and variant is not None and variant.inaccessible:
                keys = {x["point"] for x in variant.inaccessible}
                snap = seasons.adjust_snapshot(snap, ilots.lonlat, [(q.lon, q.lat) for q in placement.points],
                                               {k for k, q in enumerate(placement.points) if q.key in keys})  # fmt: skip
            e6_key = _h(e5_key, e2_key, e3_key, sp.__dict__)
            sim: SimResult = _stage(
                pv_id, st, cache, "E6", e6_key, forced_all, lambda: run_sim(snap, sp, params.seed, params.sim_mode)
            )

            # Persist the version (immutable rows, copied even when stages were cached)
            cp_ids = _persist(s, pv, ilots, placement, points.time_windows, vrp)
            new_view = plan_view(s, pv)
            pop_il = ilots.population * params.population_factor
            coverage_walk = (
                round(float(pop_il[snap.ilot_dist_m <= params.walk_distance_max_m].sum() / pop_il.sum()), 4)
                if pop_il.sum() > 0
                else None
            )
            new_view.coverage = coverage_walk

            # E7 diff
            old_view = plan_view(s, prev) if prev is not None else None
            diff = _stage(pv_id, st, cache, "E7", _h(pv_id), True, lambda: diff_plans(old_view, new_view))

            unserved_idx = vrp.solution.unserved
            pv.stages = st.stages
            pv.distance_mode = matrix.mode
            pv.summary = {
                "ilots": len(ilots.ids),
                "population": round(float(ilots.population.sum() * params.population_factor)),
                "demand_t_week": round(float(w_week.sum()), 2),
                "points": len(placement.points),
                "points_constraint_relaxed": sum(1 for p in placement.points if not p.constrained_ok),
                "placement": placement.optimisation,
                "capacite": capacite,
                **(
                    {"saisons": seasons.summary(seasons.current(), variant or seasons.Variant([], []))}
                    if seasons is not None
                    else {}
                ),  # fmt: skip
                "vrp": _vrp_quality(vrp, matrix.distance_km, demand_nodes),
                "coverage_walk": coverage_walk,
                "routes": len(vrp.solution.routes),
                "vehicles_available": len(vehicles),
                "km_day": round(sum(r.distance_km for r in vrp.solution.routes), 1),
                "cost_day_fcfa": round(sum(r.cost for r in vrp.solution.routes)),
                "unserved_points": len(unserved_idx),
                "couts": costs.estimate(
                    params,
                    sum(r.distance_km for r in vrp.solution.routes),
                    len(vehicles),
                    len({r.vehicle_idx for r in vrp.solution.routes}),
                    len(placement.points),
                    float(w_week.sum()),
                ),
                "unserved_t_per_pickup": round(float(sum(demand_nodes[i] for i in unserved_idx)), 2),
                "trucks_needed": _trucks_needed(demand_nodes, unserved_idx, vehicles),
                "distance_mode": matrix.mode,
                "solver": vrp.solution.solver,
                "notes": vrp.solution.notes,
                "dump_sites": e1.get("result", {}).get("clusters") if isinstance(e1, dict) else None,
                "sim": sim.summary,
                "sim_daily": sim.daily,
                "diff": diff,
                "duration_ms": sum(x["duration_ms"] for x in st.stages),
            }
            del cp_ids
            pv.status, pv.finished_at = "ready", utcnow()
            s.commit()
            bus.publish(
                pv_id,
                "ready",
                {"version": pv.version, "summary": {k: v for k, v in pv.summary.items() if k != "sim_daily"}},
            )
        except Exception as exc:  # the previous ready version stays served
            log.exception("pipeline failed")
            s.rollback()
            pv = s.get(PlanVersion, uuid.UUID(pv_id))
            if pv is not None:
                pv.status, pv.error, pv.finished_at = "failed", str(exc)[:2000], utcnow()
                s.commit()
            bus.publish(pv_id, "failed", {"error": str(exc)})


def _serves_area(ilot_lonlat: np.ndarray, lon: float, lat: float, walk_m: float) -> bool:
    """Un point d'une version précédente n'est gardé que s'il sert encore la zone active (zone réduite à un
    arrondissement : les points des autres quartiers disparaissent au lieu de rester figés)."""
    if not len(ilot_lonlat):
        return False
    d = np.hypot((ilot_lonlat[:, 0] - lon) * 108_700, (ilot_lonlat[:, 1] - lat) * 110_600).min()
    return bool(d <= walk_m)


def _vrp_quality(vrp: Vrp, dist_km: np.ndarray, demand: np.ndarray) -> dict[str, object]:
    """Qualité des tournées : km faits, borne inférieure garantie (vrp.lower_bound_km) et écart majorant."""
    sol = vrp.solution
    served = sorted({s for r in sol.routes for s in r.stops})
    km = float(sum(r.distance_km for r in sol.routes))
    cap = max((v.capacity_t for v in vrp.vehicles), default=0.0)
    lb = lower_bound_km(dist_km, demand, served, cap)
    return {
        "solveur": sol.solver,
        "km": round(km, 1),
        "borne_inf_km": round(lb, 1),
        "ecart_max": round((km - lb) / km, 3) if km > 0 else None,
        "duree_ms": sol.duration_ms,
        "note": "écart à une borne inférieure garantie mais faible : l'écart réel est plus petit "
        "(meilleure solution connue : docs/BENCHMARK_TOURNEES.md)",
    }


def _snapshot(ilots: Ilots, placement: PlacementResult, vrp: Vrp, params: ScenarioParams) -> PlanSnapshot:
    pts = placement.points
    dist = (
        np.array(
            [
                haversine_m(ilots.lonlat[i, 1], ilots.lonlat[i, 0], pts[a].lat, pts[a].lon) * 1.2
                for i, a in enumerate(placement.assignment)
            ]
        )
        if len(pts)
        else np.zeros(len(ilots.ids))
    )
    routes = [
        TruckRoute(
            r.vehicle_idx,
            [i - 1 for i in r.stops],
            r.distance_km,
            vrp.vehicles[r.vehicle_idx].capacity_t * 1000 if r.vehicle_idx < len(vrp.vehicles) else 8000,
            vrp.vehicles[r.vehicle_idx].fixed_cost_day
            if r.rotation == 1 and r.vehicle_idx < len(vrp.vehicles)
            else 0.0,
        )
        for r in vrp.solution.routes
    ]
    return PlanSnapshot(
        ilot_population=ilots.population,
        ilot_point=placement.assignment.astype(int),
        ilot_dist_m=dist,
        ilot_near_water=ilots.near_water,
        point_capacity_kg=np.array([p.capacity_t * 1000 for p in pts]),
        routes=routes,
        unserved_points={i - 1 for i in vrp.solution.unserved},
    )


def _persist(
    s: Session, pv: PlanVersion, ilots: Ilots, placement: PlacementResult, tws: list[tuple[int, int]], vrp: Vrp
) -> list[uuid.UUID]:
    cp_rows: list[CollectionPoint] = []
    for i, p in enumerate(placement.points):
        tw = tws[i] if i < len(tws) else DEFAULT_TW
        row = CollectionPoint(
            plan_version_id=pv.id,
            idx=i,
            key=p.key,
            geom=to_wkb(Point(p.lon, p.lat)),
            capacity_t=p.capacity_t,
            demand_t_week=round(p.demand_t_week, 3),
            ilot_ids=[ilots.ids[j] for j in p.ilots],
            tw_start=tw[0],
            tw_end=tw[1],
            label=p.key,
            frozen=p.frozen,
        )
        s.add(row)
        cp_rows.append(row)
    s.flush()
    for r, geom in zip(vrp.solution.routes, vrp.geometries, strict=True):
        v = vrp.vehicles[r.vehicle_idx]
        coords = geom if len(geom) >= 2 else geom * 2
        route = Route(
            plan_version_id=pv.id,
            vehicle_id=v.id,
            rotation=r.rotation,
            distance_km=r.distance_km,
            duration_min=r.duration_min,
            load_t=r.load_t,
            cost=r.cost,
            geom=to_wkb(LineString(coords)),
        )
        s.add(route)
        s.flush()
        for seq, (node, arr, load) in enumerate(zip(r.stops, r.arrival_min, r.load_after_t, strict=True), start=1):
            s.add(
                RouteStop(
                    route_id=route.id,
                    seq=seq,
                    collection_point_id=cp_rows[node - 1].id,
                    arrival_min=arr,
                    load_t_after=load,
                )
            )
    for node in vrp.solution.unserved:
        s.add(
            UnservedPoint(
                plan_version_id=pv.id,
                collection_point_id=cp_rows[node - 1].id,
                demand_t_week=cp_rows[node - 1].demand_t_week,
                reason="Capacité ou temps de la flotte insuffisants",
            )
        )
    s.flush()
    return [c.id for c in cp_rows]


def snapshot_from_db(s: Session, pv: PlanVersion) -> PlanSnapshot:
    """Rebuild a simulation snapshot from a stored plan version (for extra replications)."""
    pts = s.query(CollectionPoint).filter(CollectionPoint.plan_version_id == pv.id).order_by(CollectionPoint.idx).all()
    idx_of = {p.id: p.idx for p in pts}
    ilot_ids: list[uuid.UUID] = []
    assign: list[int] = []
    for p in pts:
        ilot_ids += p.ilot_ids
        assign += [p.idx] * len(p.ilot_ids)
    rows = {
        r.id: r
        for r in s.execute(
            text("""SELECT id, ST_X(centroid) AS lon, ST_Y(centroid) AS lat, population,
                     near_water FROM ilots WHERE id = ANY(:ids)"""),
            {"ids": ilot_ids},
        ).all()
    }
    params = ScenarioParams(**(pv.params_snapshot or {}))
    pop, dist, near = [], [], []
    for iid, a in zip(ilot_ids, assign, strict=True):
        r = rows[iid]
        g = shape(pts[a].geom)
        pop.append(r.population)
        dist.append(haversine_m(r.lat, r.lon, g.y, g.x) * 1.2)
        near.append(bool(r.near_water))
    vehicles = {v.id: v for v in s.query(Vehicle).filter(Vehicle.scenario_id == pv.scenario_id)}
    vidx = {vid: i for i, vid in enumerate(sorted(vehicles, key=lambda k: vehicles[k].label))}
    routes = []
    for r in s.query(Route).filter(Route.plan_version_id == pv.id):
        stops = s.query(RouteStop).filter(RouteStop.route_id == r.id).order_by(RouteStop.seq).all()
        v = vehicles[r.vehicle_id]
        routes.append(
            TruckRoute(
                vidx[r.vehicle_id],
                [idx_of[x.collection_point_id] for x in stops],
                r.distance_km,
                v.capacity_t * 1000,
                v.fixed_cost_day if r.rotation == 1 else 0.0,
            )
        )
    unserved = {
        idx_of[u.collection_point_id] for u in s.query(UnservedPoint).filter(UnservedPoint.plan_version_id == pv.id)
    }
    del params
    snap = PlanSnapshot(
        np.array(pop, dtype=float),
        np.array(assign, dtype=int),
        np.array(dist),
        np.array(near, bool),
        np.array([p.capacity_t * 1000 for p in pts]),
        routes,
        unserved,
    )
    inacc = {x["point"] for x in ((pv.summary or {}).get("saisons") or {}).get("points_inaccessibles", [])}
    if inacc and get_settings().seasons_enabled:  # module « Saisons » : ménages d'un point inaccessible
        from salubri_api.modules.seasons.service import adjust_snapshot

        il = np.array([[rows[i].lon, rows[i].lat] for i in ilot_ids])
        snap = adjust_snapshot(snap, il, [(shape(p.geom).x, shape(p.geom).y) for p in pts],
                               {p.idx for p in pts if p.key in inacc})  # fmt: skip
    return snap
