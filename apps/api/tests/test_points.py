# SPDX-License-Identifier: AGPL-3.0-or-later
import time

import numpy as np
from shapely.geometry import LineString, Point, box
from shapely.strtree import STRtree

from salubri_api.services.params import ScenarioParams
from salubri_api.services.planning.collection_points import PlacedPoint, place_points

RNG = np.random.default_rng(0)
LON0, LAT0 = -1.52, 12.35
ROADS = [LineString([(LON0 + i * 0.003, LAT0 - 0.03), (LON0 + i * 0.003, LAT0 + 0.03)]) for i in range(-10, 11)]
LAKE = box(LON0 - 0.004, LAT0 - 0.004, LON0 + 0.004, LAT0 + 0.004)
ROAD_TREE = STRtree(ROADS)


def project(pts):  # type: ignore[no-untyped-def]
    out = []
    for x, y in pts:
        p = Point(x, y)
        r = ROADS[ROAD_TREE.nearest(p)]
        q = r.interpolate(r.project(p))
        out.append((q.x, q.y))
    return out


def excluded(pts):  # type: ignore[no-untyped-def]
    return [LAKE.buffer(15 / 111_000).contains(Point(x, y)) for x, y in pts]


def ilots(n=2000):  # type: ignore[no-untyped-def]
    ll = np.column_stack([LON0 + RNG.uniform(-0.025, 0.025, n), LAT0 + RNG.uniform(-0.025, 0.025, n)])
    return ll, RNG.uniform(50, 200, n)


def test_constraints_and_capacity():
    ll, dem = ilots()
    p = ScenarioParams(collection_point_max=80)
    t0 = time.perf_counter()
    res = place_points(ll, dem, p, project=project, excluded=excluded)
    assert (time.perf_counter() - t0) < 1.5
    assert res.points and len(res.points) <= 80
    for pt in res.points:
        assert not LAKE.contains(Point(pt.lon, pt.lat))
        d = min(r.distance(Point(pt.lon, pt.lat)) for r in ROADS) * 111_000
        assert d <= 40
    assert abs(sum(pt.demand_t_week for pt in res.points) - dem.sum() * 7 / 1000) < 1e-6


def test_load_capped_when_budget_allows():
    ll, dem = ilots(600)
    p = ScenarioParams(collection_point_max=200)
    res = place_points(ll, dem, p)
    cap = p.collection_point_capacity_t * p.pickup_frequency_per_week
    assert max(pt.demand_t_week for pt in res.points) <= 1.2 * cap + 1e-9 or res.iterations == 5


def test_deterministic():
    ll, dem = ilots(500)
    a = place_points(ll, dem, ScenarioParams(), seed=1)
    b = place_points(ll, dem, ScenarioParams(), seed=1)
    assert [(x.lon, x.lat) for x in a.points] == [(x.lon, x.lat) for x in b.points]


def test_incremental_keeps_frozen_points():
    ll, dem = ilots(500)
    p = ScenarioParams()
    first = place_points(ll, dem, p)
    frozen = [PlacedPoint(x.key, x.lon, x.lat, x.capacity_t, frozen=True) for x in first.points]
    extra = np.column_stack([LON0 + 0.06 + RNG.uniform(0, 0.01, 50), LAT0 + RNG.uniform(0, 0.01, 50)])
    ll2, dem2 = np.vstack([ll, extra]), np.concatenate([dem, RNG.uniform(50, 200, 50)])
    second = place_points(ll2, dem2, p, frozen=frozen)
    kept = {x.key: (x.lon, x.lat) for x in second.points if x.frozen}
    assert kept == {f.key: (f.lon, f.lat) for f in frozen}
    new = [x for x in second.points if not x.frozen]
    assert any(x.lon > LON0 + 0.05 for x in new)  # the new area is served (gaps elsewhere may also be filled)
