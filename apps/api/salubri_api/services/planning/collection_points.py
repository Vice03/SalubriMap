# SPDX-License-Identifier: AGPL-3.0-or-later
"""Constrained placement of collection points (weighted k-means + projection on roads + exclusions).

Pure: spatial look-ups (road projection, exclusion test) are injected callables so the same code runs
against PostGIS in the API and against shapely objects in tests.
"""

import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from sklearn.cluster import KMeans

from salubri_api.services.params import ScenarioParams

ProjectFn = Callable[[list[tuple[float, float]]], list[tuple[float, float]]]
ExcludedFn = Callable[[list[tuple[float, float]]], list[bool]]

M_PER_DEG = 111_320.0


@dataclass
class PlacedPoint:
    key: str
    lon: float
    lat: float
    capacity_t: float
    demand_t_week: float = 0.0
    ilots: list[int] = field(default_factory=list)
    frozen: bool = False
    constrained_ok: bool = True


@dataclass
class PlacementResult:
    points: list[PlacedPoint]
    assignment: np.ndarray
    iterations: int
    duration_ms: int
    k: int


class LocalProj:
    """Equirectangular projection around the study area: accurate to <0.5 % over a city."""

    def __init__(self, lat0: float):
        self.kx = M_PER_DEG * math.cos(math.radians(lat0))
        self.ky = M_PER_DEG

    def xy(self, lonlat: np.ndarray) -> np.ndarray:
        return np.column_stack([lonlat[:, 0] * self.kx, lonlat[:, 1] * self.ky])

    def lonlat(self, xy: np.ndarray) -> np.ndarray:
        return np.column_stack([xy[:, 0] / self.kx, xy[:, 1] / self.ky])


def _nearest(xy_items: np.ndarray, xy_points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    d2 = ((xy_items[:, None, :] - xy_points[None, :, :]) ** 2).sum(axis=2)
    idx = d2.argmin(axis=1)
    return idx, np.sqrt(d2[np.arange(len(idx)), idx])


def _fix_constraints(
    cands: np.ndarray, proj: LocalProj, project: ProjectFn | None, excluded: ExcludedFn | None
) -> tuple[np.ndarray, list[bool]]:
    """Project each candidate onto the road network; if it falls in an exclusion zone, search a 25 m grid
    within 150 m for the closest valid road position."""
    lonlat = proj.lonlat(cands)
    pts = [tuple(p) for p in lonlat]
    if project is not None:
        pts = project(pts)  # type: ignore[arg-type]
    ok = [True] * len(pts)
    if excluded is not None:
        bad = excluded(pts)  # type: ignore[arg-type]
        for i, is_bad in enumerate(bad):
            if not is_bad:
                continue
            ok[i] = False
            cx, cy = cands[i]
            for radius, step in ((150, 25), (400, 50), (900, 100)):  # widen until we leave the exclusion zone
                grid = [
                    (cx + dx, cy + dy)
                    for dx in range(-radius, radius + 1, step)
                    for dy in range(-radius, radius + 1, step)
                    if 0 < dx * dx + dy * dy <= radius * radius
                ]
                grid.sort(key=lambda g: (g[0] - cx) ** 2 + (g[1] - cy) ** 2)
                gl = [tuple(p) for p in proj.lonlat(np.array(grid))]
                if project is not None:
                    gl = project(gl)  # type: ignore[arg-type]
                flags = excluded(gl)  # type: ignore[arg-type]
                for g, f in zip(gl, flags, strict=True):
                    if not f:
                        pts[i], ok[i] = g, True
                        break
                if ok[i]:
                    break
    return proj.xy(np.array(pts, dtype=float)), ok


def place_points(
    ilot_lonlat: np.ndarray,
    demand_kg_day: np.ndarray,
    p: ScenarioParams,
    project: ProjectFn | None = None,
    excluded: ExcludedFn | None = None,
    frozen: list[PlacedPoint] | None = None,
    seed: int = 42,
    max_iter: int = 5,
) -> PlacementResult:
    t0 = time.perf_counter()
    n = len(ilot_lonlat)
    if n == 0:
        return PlacementResult([], np.zeros(0, dtype=int), 0, 0, 0)
    proj = LocalProj(float(ilot_lonlat[:, 1].mean()))
    xy = proj.xy(ilot_lonlat)
    w_week = demand_kg_day * 7 / 1000  # t / week per ilot
    cap_week = p.collection_point_capacity_t * p.pickup_frequency_per_week
    frozen = frozen or []
    fz_xy = proj.xy(np.array([[f.lon, f.lat] for f in frozen])) if frozen else np.zeros((0, 2))

    if frozen:
        _, dist = _nearest(xy, fz_xy)
        todo = np.where(dist > p.walk_distance_max_m)[0]
    else:
        todo = np.arange(n)
    needed = max(1, math.ceil(w_week[todo].sum() / cap_week)) if len(todo) else 0
    k_budget = max(0, p.collection_point_max - len(frozen))
    if frozen:
        # A new area must be served even when the maximum is reached: the maximum bounds a full placement.
        k_budget = max(k_budget, needed)
    k = min(len(todo), k_budget, needed) if len(todo) else 0

    iterations = 0
    new_xy = np.zeros((0, 2))
    ok_flags: list[bool] = []
    while True:
        iterations += 1
        if k > 0:
            km = KMeans(n_clusters=k, n_init=5, random_state=seed)
            km.fit(xy[todo], sample_weight=np.maximum(w_week[todo], 1e-9))
            new_xy, ok_flags = _fix_constraints(km.cluster_centers_, proj, project, excluded)
        all_xy = np.vstack([fz_xy, new_xy]) if len(new_xy) else fz_xy
        assign, _ = _nearest(xy, all_xy)
        load = np.bincount(assign, weights=w_week, minlength=len(all_xy))
        overloaded = bool((load[len(frozen) :] > 1.2 * cap_week).any()) if k else False
        if not overloaded or iterations >= max_iter or k >= min(len(todo), k_budget):
            break
        k += 1

    all_ll = proj.lonlat(all_xy)
    points: list[PlacedPoint] = []
    for i in range(len(all_xy)):
        is_frozen = i < len(frozen)
        key = frozen[i].key if is_frozen else ""
        points.append(
            PlacedPoint(
                key=key,
                lon=float(all_ll[i, 0]),
                lat=float(all_ll[i, 1]),
                capacity_t=p.collection_point_capacity_t,
                demand_t_week=float(load[i]),
                ilots=np.where(assign == i)[0].tolist(),
                frozen=is_frozen,
                constrained_ok=True if is_frozen else ok_flags[i - len(frozen)],
            )
        )
    used = {pt.key for pt in points if pt.key}
    nxt = 1
    for pt in points:
        if not pt.key:
            while f"P{nxt:03d}" in used:
                nxt += 1
            pt.key = f"P{nxt:03d}"
            used.add(pt.key)
    if frozen:  # keep frozen positions bit-exact
        for i, f in enumerate(frozen):
            points[i].lon, points[i].lat = f.lon, f.lat
    return PlacementResult(points, assign, iterations, int((time.perf_counter() - t0) * 1000), len(points))
