# SPDX-License-Identifier: AGPL-3.0-or-later
"""Placement des points de regroupement comme problème d'optimisation (OR-Tools CP-SAT).

Sites candidats j (points des routes tous les ~50 m hors zones d'exclusion, centres du k-means, points existants),
îlots i de demande w_i (t/semaine). Variables : y_j (site ouvert), x_ij (îlot i servi par j), seulement pour les
paires proches (rayon de recherche ou K plus proches). Minimiser

    Σ w_i · d_ij · x_ij                      marche pondérée par la demande (t·m)
  + pénalité × w_i · d_ij · x_ij si d_ij > walk_distance_max_m      couverture : violation pénalisée
  + coût d'ouverture × Σ y_j                 un point de plus doit faire gagner assez de marche
  + Σ_e stabilité_e · (1 − y_e)              déplacer un point existant coûte

  + pénalité × walk_distance_max_m × surcharge_j          capacité dépassée (un îlot seul peut dépasser un bac)

sous : chaque îlot servi une fois ; x_ij ≤ y_j ; Σ_i w_i x_ij ≤ capacité_hebdo · y_j + surcharge_j
(surcharge_j = 0 avec `hard_capacity` : la capacité par enlèvement est alors une contrainte dure) ;
Σ y_j ≤ maximum ; points figés ouverts. d_ij = distance à vol d'oiseau × 1,2 (détour, la même valeur que la simulation).
Le k-means pondéré sert de solution de départ (indice) et de repli si CP-SAT ne trouve rien. On rend l'objectif,
la meilleure borne et l'écart (gap).
"""

import math
import time
from dataclasses import dataclass

import numpy as np

DETOUR = 1.2
SCALE = 10  # CP-SAT travaille en entiers : coûts en 0,1 t·m


@dataclass
class OptResult:
    open: list[int]  # indices des candidats ouverts
    assignment: np.ndarray  # pour chaque îlot, indice dans `open`
    status: str  # "optimal", "faisable", "repli"
    objective: float  # t·m pondérés (pénalités comprises)
    bound: float
    gap: float  # (objectif − borne) / objectif
    walk_t_m: float  # marche pondérée seule
    uncovered_t: float  # demande hors de la distance de marche (t/semaine)
    overload_t: float  # demande au-delà de la capacité des points (t/semaine)
    duration_ms: int
    warm_objective: float | None = None


def _deterministic() -> bool:
    from salubri_api.config import get_settings

    return get_settings().deterministic_solvers


def cost_matrix(xy: np.ndarray, cand: np.ndarray) -> np.ndarray:
    return np.hypot(xy[:, None, 0] - cand[None, :, 0], xy[:, None, 1] - cand[None, :, 1]) * DETOUR


def _objective(
    w: np.ndarray,
    d: np.ndarray,
    assign_c: np.ndarray,
    opened: set[int],
    walk_max: float,
    penalty: float,
    open_cost: float,
    stability: dict[int, float],
    cap_week: float,
) -> tuple[float, float, float, float]:
    di = d[np.arange(len(w)), assign_c]
    walk = float((w * di).sum())
    far = di > walk_max
    load = np.bincount(assign_c, weights=w, minlength=d.shape[1])
    overload = float(np.maximum(load - cap_week, 0).sum())
    obj = walk + penalty * float((w * di * far).sum()) + open_cost * len(opened) + penalty * walk_max * overload
    obj += sum(v for j, v in stability.items() if j not in opened)
    return obj, walk, float(w[far].sum()), overload


def optimise(
    xy: np.ndarray,
    w_week: np.ndarray,
    cand_xy: np.ndarray,
    cap_week: float,
    walk_max: float,
    max_points: int,
    fixed: list[int] | None = None,
    stability: dict[int, float] | None = None,
    warm_open: list[int] | None = None,
    open_cost: float | None = None,
    penalty: float = 10.0,
    k_nearest: int = 12,
    time_limit_s: float = 5.0,
    seed: int = 42,
    hard_capacity: bool = False,
) -> OptResult:
    from ortools.sat.python import cp_model

    t0 = time.perf_counter()
    n, m = len(xy), len(cand_xy)
    fixed = sorted(set(fixed or []))
    stability = stability or {}
    if open_cost is None:  # un point plein doit faire gagner au moins la moitié de la distance de marche
        open_cost = cap_week * walk_max / 2
    d = cost_matrix(xy, cand_xy)
    from salubri_api.config import get_settings

    if get_settings().seasons_enabled:  # module « Saisons » : paires interdites par une route impraticable
        from salubri_api.modules.seasons.service import apply_walk

        d = apply_walk(d)
    # paires considérées : à portée de marche (×1,5) ou parmi les K plus proches
    near = np.argsort(d, axis=1)[:, : min(k_nearest, m)]
    allowed = d <= 1.5 * walk_max
    allowed[np.arange(n)[:, None], near] = True
    pairs = [np.flatnonzero(allowed[i]) for i in range(n)]
    used_c = sorted(set(np.concatenate(pairs).tolist()) | set(fixed) | set(stability))

    def unit(i: int, j: int) -> int:
        c = w_week[i] * d[i, j] * (1 + penalty * (d[i, j] > walk_max))
        return int(round(c * SCALE))

    mdl = cp_model.CpModel()
    y = {j: mdl.NewBoolVar(f"y{j}") for j in used_c}
    x = {}
    for i in range(n):
        xi = []
        for j in pairs[i]:
            x[i, j] = mdl.NewBoolVar(f"x{i}_{j}")
            mdl.AddImplication(x[i, j], y[j])
            xi.append(x[i, j])
        mdl.AddExactlyOne(xi)
    cap = int(round(cap_week * 1000))
    over = {}
    tot = int(round(w_week.sum() * 1000)) + 1
    for j in used_c:
        terms = [(int(round(w_week[i] * 1000)), x[i, j]) for i in range(n) if (i, j) in x]
        if terms and hard_capacity:  # capacité par enlèvement : contrainte dure
            mdl.Add(sum(c * v for c, v in terms) <= cap * y[j])
        elif terms:
            over[j] = mdl.NewIntVar(0, tot, f"o{j}")  # kg/semaine au-delà de la capacité
            mdl.Add(sum(c * v for c, v in terms) <= cap * y[j] + over[j])
    for j in fixed:
        mdl.Add(y[j] == 1)
    mdl.Add(sum(y.values()) <= max(max_points, len(fixed)))
    obj = [unit(i, j) * v for (i, j), v in x.items()]
    obj += [int(round(open_cost * SCALE)) * v for v in y.values()]
    over_cost = max(1, int(round(penalty * walk_max * SCALE / 1000)))  # par kg/semaine
    obj += [over_cost * o for o in over.values()]
    stab_const = int(round(sum(stability.values()) * SCALE))
    obj += [-int(round(s * SCALE)) * y[j] for j, s in stability.items()]
    mdl.Minimize(sum(obj) + stab_const)

    warm_obj = None
    if warm_open:
        wo = [j for j in warm_open if j in y]
        if wo:
            for j in used_c:
                mdl.AddHint(y[j], j in wo)
            wa = np.array(wo)[d[:, wo].argmin(1)]
            for (i, j), v in x.items():
                mdl.AddHint(v, j == wa[i])
            warm_obj = _objective(w_week, d, wa, set(wo), walk_max, penalty, open_cost, stability, cap_week)[0]

    solver = cp_model.CpSolver()
    # limite en temps réel (le test en direct attend le plan) : résultat reproductible seulement à l'optimum
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_workers = 2
    solver.parameters.random_seed = seed
    if _deterministic():  # même entrée → même plan (temps déterministe, un seul fil)
        solver.parameters.num_workers = 1
        solver.parameters.max_deterministic_time = time_limit_s
        solver.parameters.max_time_in_seconds = 20 * time_limit_s
    st = solver.Solve(mdl)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        nan = math.nan
        status = "infaisable" if st == cp_model.INFEASIBLE else "repli"  # infaisable = prouvé, repli = pas trouvé
        return OptResult([], np.zeros(n, int), status, nan, nan, nan, nan, nan, nan,
                         int((time.perf_counter() - t0) * 1000), warm_obj)  # fmt: skip
    opened = [j for j in used_c if solver.Value(y[j])]
    pos = {j: k for k, j in enumerate(opened)}
    assign_c = np.array([next(j for j in pairs[i] if solver.Value(x[i, j])) for i in range(n)])
    objective = solver.ObjectiveValue() / SCALE
    bound = solver.BestObjectiveBound() / SCALE
    _, walk, uncovered, overload = _objective(
        w_week, d, assign_c, set(opened), walk_max, penalty, open_cost, stability, cap_week
    )
    return OptResult(
        opened,
        np.array([pos[j] for j in assign_c]),
        "optimal" if st == cp_model.OPTIMAL else "faisable",
        objective,
        bound,
        max(0.0, (objective - bound) / objective) if objective > 0 else 0.0,
        walk,
        uncovered,
        overload,
        int((time.perf_counter() - t0) * 1000),
        warm_obj,
    )
