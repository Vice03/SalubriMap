# SPDX-License-Identifier: AGPL-3.0-or-later
"""Constrained placement of collection points: weighted k-means (warm start and fallback), then CP-SAT
optimisation over road candidates (planning/placement_opt.py) when candidates are available.

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
# (lon_min, lat_min, lon_max, lat_max) -> candidate sites on roads, lon/lat
CandidatesFn = Callable[[tuple[float, float, float, float]], list[tuple[float, float]]]

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
    optimisation: dict[str, object] | None = None  # résumé CP-SAT (objectif, borne, écart) ou raison du repli


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


def frequencies(base: float, top: float) -> list[float]:
    """Fréquences essayées : celle du scénario, puis chaque entier au-dessus jusqu'au plafond."""
    out = [float(base)]
    f = math.floor(base) + 1
    while f <= top + 1e-9:
        out.append(float(f))
        f += 1
    return out


def effective_frequency(
    loads_week: np.ndarray, capacity_t: np.ndarray, base: float, top: float
) -> tuple[float, list[int]]:
    """Plus petite fréquence (parmi `frequencies`) où chaque point tient dans son bac à chaque enlèvement, et les
    points qui débordent encore au plafond (liste vide si tout tient)."""
    for f in frequencies(base, top):
        if not len(loads_week) or (loads_week / f <= capacity_t + 1e-9).all():
            return f, []
    f = frequencies(base, top)[-1]
    return f, np.flatnonzero(loads_week / f > capacity_t + 1e-9).tolist()


def place_points(
    ilot_lonlat: np.ndarray,
    demand_kg_day: np.ndarray,
    p: ScenarioParams,
    project: ProjectFn | None = None,
    excluded: ExcludedFn | None = None,
    frozen: list[PlacedPoint] | None = None,
    seed: int = 42,
    max_iter: int = 5,
    candidates: CandidatesFn | None = None,
    previous: list[PlacedPoint] | None = None,
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
    res = PlacementResult(points, assign, iterations, int((time.perf_counter() - t0) * 1000), len(points))
    if candidates is not None:
        res = _optimise(res, ilot_lonlat, w_week, p, proj, candidates, excluded, frozen, previous or [], seed)
        res.duration_ms = int((time.perf_counter() - t0) * 1000)
    return res


def _optimise(
    warm: PlacementResult,
    ilot_lonlat: np.ndarray,
    w_week: np.ndarray,
    p: ScenarioParams,
    proj: LocalProj,
    candidates: CandidatesFn,
    excluded: ExcludedFn | None,
    frozen: list[PlacedPoint],
    previous: list[PlacedPoint],
    seed: int,
) -> PlacementResult:
    """CP-SAT sur : points figés (ouverts), points de la version précédente (pénalité de stabilité), centres du
    k-means (solution de départ), sites des routes hors exclusions. Repli sur le k-means si rien de mieux."""
    from salubri_api.services.planning.placement_opt import optimise

    pad = p.walk_distance_max_m / M_PER_DEG
    lo, hi = ilot_lonlat.min(0) - pad, ilot_lonlat.max(0) + pad
    road = candidates((float(lo[0]), float(lo[1]), float(hi[0]), float(hi[1])))
    if road and excluded is not None:
        road = [c for c, bad in zip(road, excluded(road), strict=True) if not bad]
    cand: list[PlacedPoint] = [*warm.points[: len(frozen)]]
    prev_keys = {f.key for f in frozen}
    stab_pts = [q for q in previous if q.key not in prev_keys]
    cand += [PlacedPoint(q.key, q.lon, q.lat, p.collection_point_capacity_t) for q in stab_pts]
    warm_new = warm.points[len(frozen) :]
    cand += [PlacedPoint("", q.lon, q.lat, p.collection_point_capacity_t) for q in warm_new]
    cand += [PlacedPoint("", lon, lat, p.collection_point_capacity_t) for lon, lat in road]
    cand_xy = proj.xy(np.array([[c.lon, c.lat] for c in cand]))
    xy = proj.xy(ilot_lonlat)
    cap_week = p.collection_point_capacity_t * p.pickup_frequency_per_week
    # déplacer un point existant coûte comme faire marcher sa charge de `placement_stability_m` de plus
    stability: dict[int, float] = {}
    if stab_pts:
        prev_xy = cand_xy[len(frozen) : len(frozen) + len(stab_pts)]
        prev_assign, _ = _nearest(xy, prev_xy)
        load = np.bincount(prev_assign, weights=w_week, minlength=len(stab_pts))
        stability = {len(frozen) + k: float(load[k] * p.placement_stability_m) for k in range(len(stab_pts))}
    off = len(frozen) + len(stab_pts)
    max_points = max(p.collection_point_max, len(frozen), len(warm.points))
    warm_open = list(range(len(frozen))) + (
        list(range(len(frozen), off)) if stab_pts else list(range(off, off + len(warm_new)))
    )  # départ : les points de la version précédente s'il y en a (stabilité), sinon le k-means

    def run(cap_w: float, hard: bool):  # type: ignore[no-untyped-def]
        return optimise(
            xy,
            w_week,
            cand_xy,
            cap_w,
            p.walk_distance_max_m,
            max_points,
            fixed=list(range(len(frozen))),
            stability=stability,
            warm_open=warm_open,
            time_limit_s=p.placement_time_limit_s,
            seed=seed,
            hard_capacity=hard,
        )

    # Capacité par enlèvement = contrainte dure : demande hebdomadaire ÷ enlèvements ≤ capacité du point. On essaie
    # la fréquence demandée, puis une de plus jusqu'au plafond ; sinon on le dit et on garde le placement pénalisé.
    essais: list[dict[str, object]] = []
    r = None
    freq = p.pickup_frequency_per_week
    for f in frequencies(p.pickup_frequency_per_week, p.pickup_frequency_max_per_week):
        rr = run(p.collection_point_capacity_t * f, True)
        essais.append({"enlevements_semaine": f, "statut": rr.status})
        if rr.status in ("optimal", "faisable"):
            r, freq = rr, f
            break
    capacite: dict[str, object] = {"contrainte": "dure", "essais": essais}
    if r is None:
        r = run(cap_week, False)
        capacite["contrainte"] = "non respectée"
        prouve = all(e["statut"] == "infaisable" for e in essais)
        capacite["raison"] = (
            f"Aucun placement de {max_points} points au plus ne tient dans la capacité des bacs, même à "
            f"{p.pickup_frequency_max_per_week:g} enlèvements par semaine : ajouter des points (maximum), des bacs "
            "plus grands ou des enlèvements"
            if prouve
            else "CP-SAT n'a pas trouvé, dans le temps imparti, de placement qui tienne dans la capacité : placement "
            "pénalisé gardé (des points peuvent déborder)"
        )
        freq = p.pickup_frequency_per_week
    capacite["enlevements_semaine"] = freq
    info: dict[str, object] = {
        "methode": "CP-SAT",
        "statut": r.status,
        "candidats": len(cand),
        "candidats_routes": len(road),
        "objectif": None if math.isnan(r.objective) else round(r.objective, 1),
        "borne": None if math.isnan(r.bound) else round(r.bound, 1),
        "ecart": None if math.isnan(r.gap) else round(r.gap, 4),
        "depart": "version précédente" if stab_pts else "k-means",
        "objectif_depart": None if r.warm_objective is None else round(r.warm_objective, 1),
        "marche_t_m": None if math.isnan(r.walk_t_m) else round(r.walk_t_m, 1),
        "demande_hors_marche_t_semaine": None if math.isnan(r.uncovered_t) else round(r.uncovered_t, 3),
        "surcharge_t_semaine": None if math.isnan(r.overload_t) else round(r.overload_t, 3),
        "duree_ms": r.duration_ms,
        "capacite": capacite,
    }
    if r.status == "repli":  # sinon la solution part de l'indice : au moins aussi bonne, aux arrondis près
        info["statut"] = "repli"
        info["raison"] = "CP-SAT sans solution meilleure que le k-means dans le temps imparti"
        warm.optimisation = info
        return warm
    load = np.bincount(r.assignment, weights=w_week, minlength=len(r.open))
    pts: list[PlacedPoint] = []
    for k, j in enumerate(r.open):
        c = cand[j]
        pts.append(
            PlacedPoint(
                c.key,
                c.lon,
                c.lat,
                p.collection_point_capacity_t,
                float(load[k]),
                np.flatnonzero(r.assignment == k).tolist(),
                frozen=j < len(frozen),
                constrained_ok=True,
            )
        )
    used = {q.key for q in pts if q.key}
    nxt = 1
    for q in pts:
        if not q.key:
            while f"P{nxt:03d}" in used:
                nxt += 1
            q.key = f"P{nxt:03d}"
            used.add(q.key)
    info["points_conserves"] = sum(1 for j in r.open if len(frozen) <= j < off)
    return PlacementResult(pts, r.assignment.astype(int), warm.iterations, 0, len(pts), info)
