# SPDX-License-Identifier: AGPL-3.0-or-later
import time

import numpy as np

from salubri_api.services.params import ScenarioParams
from salubri_api.services.simulation.agents import PlanSnapshot, TruckRoute
from salubri_api.services.simulation.engine import replicate, simulate
from salubri_api.services.simulation.params import SimParams

RNG = np.random.default_rng(0)
N, P = 300, 45


def plan(routes=True, n_routes=15):  # type: ignore[no-untyped-def]
    r = (
        [TruckRoute(i % 8, list(range(i * 3, min(P, i * 3 + 3))), 20, 8000, 20000) for i in range(n_routes)]
        if routes
        else []
    )
    return PlanSnapshot(
        RNG.uniform(150, 250, N),
        RNG.integers(0, P, N),
        RNG.uniform(50, 600, N),
        RNG.random(N) < 0.1,
        np.full(P, 2500.0),
        r,
    )


PLAN = plan()


def sp(**kw):  # type: ignore[no-untyped-def]
    return SimParams.from_scenario(ScenarioParams(**kw))


def test_mass_balance_and_speed():
    t0 = time.perf_counter()
    res = simulate(PLAN, sp(), 42)
    assert time.perf_counter() - t0 < 2
    assert res.summary["mass_balance_error"] < 1e-6


def test_deterministic():
    assert simulate(PLAN, sp(), 1).summary == simulate(PLAN, sp(), 1).summary


def test_no_trucks_means_overflow_and_growing_dumps():
    res = simulate(plan(routes=False), sp(), 42)
    assert res.summary["overflow_point_days"] > 0
    assert res.daily["wild_stock_t"][-1] > res.daily["wild_stock_t"][10]


def test_more_cleanup_fewer_dumps():
    small = simulate(PLAN, sp(cleanup_capacity_t_day=2), 42).summary["wild_dumps_active_mean"]
    big = simulate(PLAN, sp(cleanup_capacity_t_day=40), 42).summary["wild_dumps_active_mean"]
    assert big < small


def test_laabal_deters_dumping_without_collecting():
    base = dict(cleanup_capacity_t_day=2)
    off = simulate(PLAN, sp(laabal_operations_per_week=0, **base), 42).summary
    on = simulate(PLAN, sp(laabal_operations_per_week=7, laabal_deterrence=0.8, **base), 42).summary
    assert off["laabal_controls"] == 0 and on["laabal_controls"] > 0
    assert on["wild_dump_t"] < off["wild_dump_t"]
    assert on["subscription_rate_final"] >= off["subscription_rate_final"]
    assert on["mass_balance_error"] < 1e-6


def test_legacy_laabal_capacity_key_maps_to_cleanup():
    assert ScenarioParams(laabal_capacity_t_day=7).cleanup_capacity_t_day == 7


def test_rain_produces_15_percent_more():
    dry = simulate(PLAN, sp(season="dry"), 42).summary["produced_t"]
    rain = simulate(PLAN, sp(season="rain"), 42).summary["produced_t"]
    assert abs(rain / dry - 1.15) < 1e-3


def test_replications_give_bands():
    out = replicate(PLAN, sp(truck_breakdown_rate_per_day=0.2), 42, 5)
    s = out["summary"]["collected_t"]
    assert s["p10"] <= s["median"] <= s["p90"]


def test_parameter_uncertainty_widens_intervals():
    """Revue r7, F4 : l'intervalle « bruit + paramètres non calés » est publié à côté de l'intervalle des graines."""
    from salubri_api.services.simulation.engine import replicate

    base = replicate(PLAN, sp(), seed=3, n=12)
    both = replicate(PLAN, sp(), seed=3, n=12, uncertainty=True)
    w = both["summary"]["wild_dump_t"]
    assert base["summary"]["wild_dump_t"]["median"] == w["median"]  # la série « graines » ne change pas
    assert w["p5_param"] <= w["median_param"] <= w["p95_param"]
    assert (w["p95_param"] - w["p5_param"]) > (w["p95"] - w["p5"])
    assert "p5_param" not in base["summary"]["wild_dump_t"]
