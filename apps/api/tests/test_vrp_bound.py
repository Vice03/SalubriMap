# SPDX-License-Identifier: AGPL-3.0-or-later
"""La borne inférieure des km de tournée ne dépasse jamais l'optimum (énumération sur de petites instances)."""

import itertools

import numpy as np

from salubri_api.services.planning.vrp import STRATEGIES, VehicleSpec, lower_bound_km, solve_vrp


def optimum_km(d: np.ndarray, q: np.ndarray, cap: float) -> float:
    """Meilleur découpage en tournées (ordre des points énuméré, coupé dès que la capacité est atteinte)."""
    n = len(q) - 1
    best = np.inf
    for perm in itertools.permutations(range(1, n + 1)):
        for cuts in itertools.product([0, 1], repeat=n - 1):
            km, load, prev, ok = 0.0, 0.0, 0, True
            for k, i in enumerate(perm):
                if load + q[i] > cap + 1e-9:
                    ok = False
                    break
                km += d[prev, i]
                load += q[i]
                prev = i
                if k < n - 1 and cuts[k]:
                    km += d[prev, 0]
                    load, prev = 0.0, 0
            if ok:
                best = min(best, km + d[prev, 0])
    return best


def test_borne_toujours_sous_l_optimum() -> None:
    rng = np.random.default_rng(0)
    for _ in range(5):
        xy = rng.uniform(0, 10, (6, 2))
        d = np.hypot(*(xy[:, None, :] - xy[None, :, :]).transpose(2, 0, 1))
        q = np.r_[0, rng.uniform(1, 4, 5)]
        for cap in (5.0, 100.0):
            assert lower_bound_km(d, q, list(range(1, 6)), cap) <= optimum_km(d, q, cap) + 1e-9


def test_strategies_de_depart_utilisables() -> None:
    rng = np.random.default_rng(1)
    xy = rng.uniform(0, 5, (8, 2))
    d = np.hypot(*(xy[:, None, :] - xy[None, :, :]).transpose(2, 0, 1))
    q = np.r_[0, np.full(7, 1.0)]
    v = [VehicleSpec(4, 500, 10000)]
    for s in STRATEGIES:
        sol = solve_vrp(d, d * 2, q, v, [(0, 1440)] * 8, 5, time_limit_s=0.5, first_solution=s)
        km = sum(r.distance_km for r in sol.routes)
        assert not sol.unserved and km >= lower_bound_km(d, q, list(range(1, 8)), 4) - 1e-9
