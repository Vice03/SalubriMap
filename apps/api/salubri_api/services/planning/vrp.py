# SPDX-License-Identifier: AGPL-3.0-or-later
"""Capacitated VRP with time windows (OR-Tools), multi-rotation, droppable stops. Node 0 is the depot."""

import time
from dataclasses import dataclass, field

import numpy as np

SCALE = 1000  # OR-Tools works on integers: tonnes -> kg, km -> m


@dataclass
class VehicleSpec:
    capacity_t: float
    cost_per_km: float
    fixed_cost: float
    shift_start: int = 300
    shift_end: int = 1080
    ref: str = ""


@dataclass
class RouteOut:
    vehicle_idx: int
    rotation: int
    stops: list[int]
    arrival_min: list[float]
    load_after_t: list[float]
    load_t: float
    distance_km: float
    duration_min: float
    cost: float


@dataclass
class VrpSolution:
    routes: list[RouteOut]
    unserved: list[int]
    objective: float
    solver: str
    duration_ms: int
    notes: list[str] = field(default_factory=list)


def route_stats(
    stops: list[int],
    dist: np.ndarray,
    dur: np.ndarray,
    demand: np.ndarray,
    service_min: float,
    start_min: float,
    tw: list[tuple[int, int]],
) -> tuple[list[float], list[float], float, float, float]:
    t, load, d = float(start_min), 0.0, 0.0
    arr, loads = [], []
    prev = 0
    for s in stops:
        t += float(dur[prev, s])
        d += float(dist[prev, s])
        t = max(t, float(tw[s][0]))
        arr.append(round(t, 1))
        load += float(demand[s])
        loads.append(round(load, 3))
        t += service_min
        prev = s
    t += float(dur[prev, 0])
    d += float(dist[prev, 0])
    return arr, loads, round(load, 3), round(d, 3), round(t - start_min, 1)


def solve_vrp(
    dist_km: np.ndarray,
    dur_min: np.ndarray,
    demand_t: np.ndarray,
    vehicles: list[VehicleSpec],
    time_windows: list[tuple[int, int]],
    service_min: float = 10,
    max_route_min: float = 480,
    time_limit_s: float = 2.0,
    rotations: int = 2,
    drop_penalty: int = 10_000_000,
    first_solution: str = "PARALLEL_CHEAPEST_INSERTION",
) -> VrpSolution:
    t0 = time.perf_counter()
    n = len(demand_t)
    if n <= 1:
        return VrpSolution([], [], 0.0, "ortools", 0)
    if not vehicles:
        return VrpSolution([], list(range(1, n)), 0.0, "none", 0, ["Aucun camion disponible"])
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except ImportError:
        from salubri_api.services.planning.vrp_fallback import solve_fallback

        return solve_fallback(dist_km, dur_min, demand_t, vehicles, time_windows, service_min, max_route_min, rotations)

    fleet: list[tuple[int, int]] = [(vi, r) for vi in range(len(vehicles)) for r in range(rotations)]
    m = len(fleet)
    manager = pywrapcp.RoutingIndexManager(n, m, 0)
    routing = pywrapcp.RoutingModel(manager)
    dist_i = np.rint(dist_km * SCALE).astype(int)
    dur_i = np.rint(dur_min).astype(int)
    # demandes arrondies au kg supérieur, capacités au kg inférieur : la charge réelle ne dépasse jamais la
    # capacité (un arrondi au plus proche laissait passer 8,001 t dans un camion de 8 t)
    dem_i = np.ceil(np.round(demand_t * SCALE, 6)).astype(int)
    svc = int(service_min)

    for v, (vi, rot) in enumerate(fleet):
        per_m = vehicles[vi].cost_per_km / SCALE
        mat = np.rint(dist_i * per_m).astype(int)

        def cost_cb(a: int, b: int, mat: np.ndarray = mat) -> int:
            return int(mat[manager.IndexToNode(a), manager.IndexToNode(b)])

        cb = routing.RegisterTransitCallback(cost_cb)
        routing.SetArcCostEvaluatorOfVehicle(cb, v)
        routing.SetFixedCostOfVehicle(int(vehicles[vi].fixed_cost) if rot == 0 else 0, v)

    def demand_cb(a: int) -> int:
        return int(dem_i[manager.IndexToNode(a)])

    dcb = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(
        dcb, 0, [int(np.floor(round(vehicles[vi].capacity_t * SCALE, 6))) for vi, _ in fleet], True, "Capacity"
    )

    def time_cb(a: int, b: int) -> int:
        i, j = manager.IndexToNode(a), manager.IndexToNode(b)
        return int(dur_i[i, j]) + (svc if i != 0 else 0)

    tcb = routing.RegisterTransitCallback(time_cb)
    horizon = 24 * 60
    routing.AddDimension(tcb, 120, horizon, False, "Time")
    tdim = routing.GetDimensionOrDie("Time")
    for node in range(1, n):
        idx = manager.NodeToIndex(node)
        tdim.CumulVar(idx).SetRange(int(time_windows[node][0]), int(time_windows[node][1]))
        routing.AddDisjunction([idx], int(drop_penalty))
    # Rotation r of a truck starts after rotation r-1 ends: enforce by sequencing start windows.
    for v, (vi, rot) in enumerate(fleet):
        spec = vehicles[vi]
        start, end = routing.Start(v), routing.End(v)
        tdim.CumulVar(start).SetRange(spec.shift_start, spec.shift_end)
        tdim.CumulVar(end).SetRange(spec.shift_start, spec.shift_end)
        routing.solver().Add(tdim.CumulVar(end) - tdim.CumulVar(start) <= int(max_route_min))
        if rot > 0:
            prev_v = fleet.index((vi, rot - 1))
            routing.solver().Add(tdim.CumulVar(start) >= tdim.CumulVar(routing.End(prev_v)))
        routing.AddVariableMinimizedByFinalizer(tdim.CumulVar(end))

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = getattr(routing_enums_pb2.FirstSolutionStrategy, first_solution)
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    # Large instances (whole city: 1,000+ points) need more than the default second to get past the first
    # insertion pass; under that limit OR-Tools can return an almost empty solution (every point dropped).
    params.time_limit.FromMilliseconds(int(effective_time_limit(time_limit_s, n) * 1000))
    sol = routing.SolveWithParameters(params)
    if sol is None:
        from salubri_api.services.planning.vrp_fallback import solve_fallback

        res = solve_fallback(dist_km, dur_min, demand_t, vehicles, time_windows, service_min, max_route_min, rotations)
        res.notes.append("OR-Tools sans solution dans le temps imparti : heuristique de repli")
        return res

    routes: list[RouteOut] = []
    visited: set[int] = set()
    for v, (vi, rot) in enumerate(fleet):
        idx = routing.Start(v)
        stops: list[int] = []
        start_t = sol.Value(tdim.CumulVar(idx))
        idx = sol.Value(routing.NextVar(idx))
        while not routing.IsEnd(idx):
            stops.append(manager.IndexToNode(idx))
            idx = sol.Value(routing.NextVar(idx))
        if not stops:
            continue
        visited.update(stops)
        arr, loads, load, d, dur = route_stats(stops, dist_km, dur_min, demand_t, service_min, start_t, time_windows)
        cost = d * vehicles[vi].cost_per_km + (vehicles[vi].fixed_cost if rot == 0 else 0)
        routes.append(RouteOut(vi, rot + 1, stops, arr, loads, load, d, dur, round(cost, 0)))
    unserved = [i for i in range(1, n) if i not in visited]
    # Rotation numbers in output = order of use per truck.
    by_vehicle: dict[int, int] = {}
    for r in sorted(routes, key=lambda r: (r.vehicle_idx, r.arrival_min[0])):
        by_vehicle[r.vehicle_idx] = by_vehicle.get(r.vehicle_idx, 0) + 1
        r.rotation = by_vehicle[r.vehicle_idx]
    best = VrpSolution(routes, unserved, float(sol.ObjectiveValue()), "ortools", int((time.perf_counter() - t0) * 1000))
    if unserved:
        # Stopped by the time limit with points left over: the constructive heuristic may serve more.
        from salubri_api.services.planning.vrp_fallback import solve_fallback

        fb = solve_fallback(dist_km, dur_min, demand_t, vehicles, time_windows, service_min, max_route_min, rotations)
        if _left_t(fb.unserved, demand_t) < _left_t(unserved, demand_t) - 1e-9:
            fb.notes.append("Heuristique de repli retenue : elle dessert plus que OR-Tools dans le temps imparti")
            fb.duration_ms = int((time.perf_counter() - t0) * 1000)
            return fb
    return best


def effective_time_limit(time_limit_s: float, n_nodes: int) -> float:
    """Scenario time limit, raised for large instances (about 1 s per 300 points, at most 8 s)."""
    return max(time_limit_s, min(8.0, n_nodes / 300))


def _left_t(unserved: list[int], demand_t: np.ndarray) -> float:
    return float(sum(demand_t[i] for i in unserved))


STRATEGIES = ["PARALLEL_CHEAPEST_INSERTION", "PATH_CHEAPEST_ARC", "SAVINGS"]  # 3 départs pour la meilleure connue


def lower_bound_km(dist_km: np.ndarray, demand_t: np.ndarray, served: list[int], capacity_max_t: float) -> float:
    """Borne inférieure valide des km pour desservir `served` depuis le dépôt (nœud 0), distances symétrisées.

    - borne radiale : chaque tonne doit aller du point au dépôt et en revenir, un camion porte au plus
      `capacity_max_t` : km ≥ 2 · Σ q_i · d(0, i) / Q ;
    - point le plus lointain : au moins un aller-retour, km ≥ 2 · max d(0, i).
    Faible quand les points sont proches du dépôt, mais garantie : l'écart rapporté est un majorant de l'écart réel.
    """
    if not served or capacity_max_t <= 0:
        return 0.0
    d0 = np.minimum(dist_km[0, served], dist_km[served, 0])
    radial = 2 * float((demand_t[served] * d0).sum()) / capacity_max_t
    return max(radial, 2 * float(d0.max()))
