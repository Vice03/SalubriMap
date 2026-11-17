# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mode « solveurs reproductibles » (contrôles modules éteints) : même entrée → même placement, mêmes tournées."""

import numpy as np

from salubri_api.config import get_settings
from salubri_api.services.planning.distance import approx_matrix
from salubri_api.services.planning.placement_opt import optimise
from salubri_api.services.planning.vrp import VehicleSpec, solve_vrp


def test_deterministic_mode_reproduces_placement_and_routes(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(get_settings(), "deterministic_solvers", True)
    rng = np.random.default_rng(7)
    xy = rng.uniform(0, 3000, (120, 2))
    w = rng.uniform(0.2, 1.5, 120)
    cand = rng.uniform(0, 3000, (200, 2))
    a = optimise(xy, w, cand, 5.0, 300, 40, time_limit_s=0.5)
    b = optimise(xy, w, cand, 5.0, 300, 40, time_limit_s=0.5)
    assert a.open == b.open and (a.assignment == b.assignment).all()
    nodes = [(-1.52, 12.37)] + [(-1.52 + rng.uniform(-0.03, 0.03), 12.37 + rng.uniform(-0.03, 0.03)) for _ in range(40)]
    m = approx_matrix(nodes, "dry")
    dem = np.array([0.0] + [1.5] * 40)
    fleet = [VehicleSpec(8, 450, 20000) for _ in range(3)]
    r1 = solve_vrp(m.distance_km, m.duration_min, dem, fleet, [(0, 1440)] * 41, time_limit_s=0.3)
    r2 = solve_vrp(m.distance_km, m.duration_min, dem, fleet, [(0, 1440)] * 41, time_limit_s=0.3)
    assert [r.stops for r in r1.routes] == [r.stops for r in r2.routes]


def test_off_by_default() -> None:
    assert get_settings().deterministic_solvers is False
