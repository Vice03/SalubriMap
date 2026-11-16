# SPDX-License-Identifier: AGPL-3.0-or-later
"""Clarke-Wright savings + 2-opt. Always answers quickly; used when OR-Tools is missing or finds nothing."""

import time

import numpy as np

from salubri_api.services.planning.vrp import RouteOut, VehicleSpec, VrpSolution, route_stats


def _two_opt(route: list[int], dist: np.ndarray) -> list[int]:
    best = route[:]
    improved = True
    while improved:
        improved = False
        path = [0] + best + [0]
        for i in range(1, len(path) - 2):
            for j in range(i + 1, len(path) - 1):
                a, b, c, d = path[i - 1], path[i], path[j], path[j + 1]
                if dist[a, c] + dist[b, d] < dist[a, b] + dist[c, d] - 1e-9:
                    path[i : j + 1] = reversed(path[i : j + 1])
                    improved = True
        best = path[1:-1]
    return best


def solve_fallback(
    dist_km: np.ndarray,
    dur_min: np.ndarray,
    demand_t: np.ndarray,
    vehicles: list[VehicleSpec],
    time_windows: list[tuple[int, int]],
    service_min: float = 10,
    max_route_min: float = 480,
    rotations: int = 2,
) -> VrpSolution:
    t0 = time.perf_counter()
    n = len(demand_t)
    if not vehicles:
        return VrpSolution([], list(range(1, n)), 0.0, "fallback", 0, ["Aucun camion disponible"])
    cap = min(v.capacity_t for v in vehicles)  # every tour then fits every truck
    routes: list[list[int]] = [[i] for i in range(1, n)]
    where = {i: i - 1 for i in range(1, n)}
    savings = sorted(
        ((dist_km[0, i] + dist_km[0, j] - dist_km[i, j], i, j) for i in range(1, n) for j in range(i + 1, n)),
        reverse=True,
    )
    for _, i, j in savings:
        ri, rj = where[i], where[j]
        if ri == rj or not routes[ri] or not routes[rj]:
            continue
        a, b = routes[ri], routes[rj]
        if demand_t[a].sum() + demand_t[b].sum() > cap:
            continue
        if a[-1] == i and b[0] == j:
            merged = a + b
        elif b[-1] == j and a[0] == i:
            merged = b + a
        elif a[0] == i and b[0] == j:
            merged = a[::-1] + b
        elif a[-1] == i and b[-1] == j:
            merged = a + b[::-1]
        else:
            continue
        routes[ri], routes[rj] = merged, []
        for k in merged:
            where[k] = ri
    tours = sorted((_two_opt(r, dist_km) for r in routes if r), key=lambda r: -demand_t[r].sum())
    slots = sorted(
        ((vi, rot) for vi in range(len(vehicles)) for rot in range(rotations)),
        key=lambda x: (x[1], -vehicles[x[0]].capacity_t),
    )
    clock = {vi: float(v.shift_start) for vi, v in enumerate(vehicles)}
    out: list[RouteOut] = []
    unserved: list[int] = []
    used = set()
    for tour in tours:
        placed = False
        for vi, rot in slots:
            if (vi, rot) in used or demand_t[tour].sum() > vehicles[vi].capacity_t:
                continue
            arr, loads, load, d, dur = route_stats(
                tour, dist_km, dur_min, demand_t, service_min, clock[vi], time_windows
            )
            if dur > max_route_min or clock[vi] + dur > vehicles[vi].shift_end:
                continue
            used.add((vi, rot))
            clock[vi] += dur
            cost = d * vehicles[vi].cost_per_km + (vehicles[vi].fixed_cost if rot == 0 else 0)
            out.append(RouteOut(vi, rot + 1, tour, arr, loads, load, d, dur, round(cost, 0)))
            placed = True
            break
        if not placed:
            unserved.extend(tour)
    obj = sum(r.cost for r in out) + 10_000 * len(unserved)
    return VrpSolution(out, sorted(unserved), obj, "fallback", int((time.perf_counter() - t0) * 1000))
