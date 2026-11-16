# SPDX-License-Identifier: AGPL-3.0-or-later
import time

import numpy as np
import pytest

from salubri_api.services.planning.distance import approx_matrix, build_matrix
from salubri_api.services.planning.vrp import VehicleSpec, solve_vrp
from salubri_api.services.planning.vrp_fallback import solve_fallback

RNG = np.random.default_rng(3)
NODES = [(-1.50, 12.40)] + [(-1.52 + RNG.uniform(-0.02, 0.02), 12.35 + RNG.uniform(-0.02, 0.02)) for _ in range(30)]
M = approx_matrix(NODES, "dry")
DEM = np.array([0.0] + [2.0] * 30)
TW = [(0, 1440)] + [(420, 1020)] * 25 + [(300, 480)] * 5
FLEET = [VehicleSpec(8, 450, 20000) for _ in range(3)] + [VehicleSpec(12, 520, 25000)]


@pytest.mark.parametrize("solver", [solve_vrp, solve_fallback])
def test_capacity_and_feasibility(solver):
    sol = solver(M.distance_km, M.duration_min, DEM, FLEET, TW)
    seen = [s for r in sol.routes for s in r.stops] + sol.unserved
    assert sorted(seen) == list(range(1, 31))  # every point either served once or reported
    for r in sol.routes:
        assert r.load_t <= FLEET[r.vehicle_idx].capacity_t + 1e-6


def test_time_windows_respected_ortools():
    sol = solve_vrp(M.distance_km, M.duration_min, DEM, FLEET, TW, time_limit_s=1.0)
    for r in sol.routes:
        for node, arr in zip(r.stops, r.arrival_min, strict=True):
            assert TW[node][0] - 1 <= arr <= TW[node][1] + 1


def test_no_vehicle_means_everything_unserved():
    sol = solve_vrp(M.distance_km, M.duration_min, DEM, [], TW)
    assert sol.routes == [] and sol.unserved == list(range(1, 31))


def test_insufficient_fleet_drops_points_not_crash():
    sol = solve_vrp(M.distance_km, M.duration_min, DEM, [VehicleSpec(8, 450, 20000)], TW, time_limit_s=0.5)
    assert sol.unserved and sum(r.load_t for r in sol.routes) <= 16 + 1e-6


def test_time_limit():
    t0 = time.perf_counter()
    solve_vrp(M.distance_km, M.duration_min, DEM, FLEET, TW, time_limit_s=1.0)
    assert time.perf_counter() - t0 < 2.5


def test_osrm_down_falls_back_to_haversine():
    m = build_matrix(NODES[:5], "dry", "http://127.0.0.1:9", timeout=0.3)
    assert m.mode == "approx" and m.distance_km.shape == (5, 5)


def test_rain_is_slower():
    dry, rain = approx_matrix(NODES[:5], "dry"), approx_matrix(NODES[:5], "rain")
    assert (rain.duration_min[0, 1:] > dry.duration_min[0, 1:]).all()


def test_time_limited_ortools_never_serves_less_than_the_fallback() -> None:
    """Large instance + tiny time limit: OR-Tools may stop with most points dropped; keep the better plan."""
    from salubri_api.services.planning.vrp import effective_time_limit
    from salubri_api.services.planning.vrp_fallback import solve_fallback

    rng = np.random.default_rng(1)
    n = 301
    xy = rng.uniform(0, 25, (n, 2))
    dist = np.hypot(*(xy[:, None, :] - xy[None, :, :]).transpose(2, 0, 1))
    dur = dist / 25 * 90
    dem = np.r_[0, rng.uniform(0.3, 2.5, n - 1)]
    veh = [VehicleSpec(8, 450, 20000)] * 4
    tw = [(0, 1440)] + [(420, 1020)] * (n - 1)
    sol = solve_vrp(dist, dur, dem, veh, tw, 10, time_limit_s=0.02)
    fb = solve_fallback(dist, dur, dem, veh, tw, 10, 480, 2)
    left = lambda u: sum(dem[i] for i in u)  # noqa: E731
    assert sol.routes
    assert left(sol.unserved) <= left(fb.unserved) + 1e-9
    assert effective_time_limit(1.0, 56) == 1.0
    assert effective_time_limit(1.0, 1035) > 3
