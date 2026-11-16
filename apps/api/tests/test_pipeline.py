# SPDX-License-Identifier: AGPL-3.0-or-later
"""Recompute pipeline: caching per stage, immutability, incremental points, failure isolation, merging."""

import time

from salubri_api.models import PlanVersion, Scenario, Vehicle
from salubri_api.services.plan import pipeline
from salubri_api.services.plan.pipeline import request_recompute


def scenario(db):  # type: ignore[no-untyped-def]
    return db.query(Scenario).first()


def ran(pv):  # type: ignore[no-untyped-def]
    return {s["stage"] for s in pv.stages if not s["cache_hit"]}


def first_plan(db):  # type: ignore[no-untyped-def]
    pv = request_recompute(db, scenario(db), "manual", sync=True)
    assert pv.status == "ready", pv.error
    return pv


def test_first_plan_is_complete(db, client):
    pv = first_plan(db)
    s = pv.summary
    assert s["points"] > 0 and s["routes"] > 0 and s["distance_mode"] == "approx"
    assert s["sim"]["mass_balance_error"] < 1e-6
    pts = client.get(f"/api/plans/{pv.id}/points").json()["features"]
    routes = client.get(f"/api/plans/{pv.id}/routes").json()["features"]
    assert len(pts) == s["points"] and len(routes) == s["routes"]
    for r in routes:
        assert r["properties"]["load_t"] <= r["properties"]["capacity_t"] + 1e-6
        assert r["geometry"]["type"] == "LineString" and r["properties"]["stops"]


def test_breakdown_reuses_e1_to_e4(db):
    first_plan(db)
    sc = scenario(db)
    v = db.query(Vehicle).filter(Vehicle.scenario_id == sc.id).order_by(Vehicle.label).first()
    v.out_of_service = True
    db.commit()
    t0 = time.perf_counter()
    pv = request_recompute(db, sc, "fleet_changed", sync=True)
    assert time.perf_counter() - t0 < 2.0
    assert pv.status == "ready" and ran(pv) == {"E5", "E6", "E7"}
    assert pv.summary["vehicles_available"] == 3


def test_season_recomputes_matrix_keeps_points(db, client):
    a = first_plan(db)
    sc = scenario(db)
    sc.params = {**sc.params, "season": "rain"}
    db.commit()
    b = request_recompute(db, sc, "season_changed", sync=True)
    assert {"E2", "E4", "E5"} <= ran(b) and "E3" not in ran(b)
    pa = {
        f["properties"]["key"]: f["geometry"]["coordinates"]
        for f in client.get(f"/api/plans/{a.id}/points").json()["features"]
    }
    pb = {
        f["properties"]["key"]: f["geometry"]["coordinates"]
        for f in client.get(f"/api/plans/{b.id}/points").json()["features"]
    }
    assert pa == pb
    assert b.summary["demand_t_week"] > a.summary["demand_t_week"]


def test_new_quartier_freezes_existing_points(db, client):
    a = first_plan(db)
    before = {
        f["properties"]["key"]: f["geometry"]["coordinates"]
        for f in client.get(f"/api/plans/{a.id}/points").json()["features"]
    }
    poly = [[-1.556, 12.376], [-1.53, 12.376], [-1.53, 12.379], [-1.556, 12.379], [-1.556, 12.376]]
    body = client.post(
        "/api/quartiers",
        json={
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [poly]},
            "properties": {"name": "Nouveau", "population": 6000},
        },
    ).json()
    pid = body["plans"][0]["plan_version_id"]
    for _ in range(100):
        st = client.get(f"/api/plans/{pid}").json()
        if st["status"] in ("ready", "failed"):
            break
        time.sleep(0.1)
    assert st["status"] == "ready", st
    after = {
        f["properties"]["key"]: f["geometry"]["coordinates"]
        for f in client.get(f"/api/plans/{pid}/points").json()["features"]
    }
    for k, xy in before.items():
        assert after[k] == xy
    assert len(after) > len(before)
    assert any(12.37 <= xy[1] <= 12.385 for k, xy in after.items() if k not in before)
    assert client.delete(f"/api/quartiers/{body['quartier']['properties']['id']}").status_code == 204


def test_failure_keeps_previous_ready(db, monkeypatch):
    a = first_plan(db)

    def boom(*a, **k):  # type: ignore[no-untyped-def]
        raise RuntimeError("panne simulée")

    monkeypatch.setattr(pipeline, "solve_vrp", boom)
    sc = scenario(db)
    sc.params = {**sc.params, "vrp_time_limit_s": 0.6}
    db.commit()
    b = request_recompute(db, sc, "fleet_changed", sync=True)
    assert b.status == "failed" and "panne simulée" in b.error
    assert pipeline.latest_ready(db, sc.id).id == a.id


def test_concurrent_requests_end_with_one_ready(db):
    first_plan(db)
    sc = scenario(db)
    pv1 = request_recompute(db, sc, "budget_changed")
    pv2 = request_recompute(db, sc, "fleet_changed")
    pv3 = request_recompute(db, sc, "subscription_changed")
    deadline = time.time() + 20
    while time.time() < deadline:
        db.expire_all()
        st = {p.id: p.status for p in db.query(PlanVersion).filter(PlanVersion.id.in_([pv1.id, pv2.id, pv3.id]))}
        if all(s in ("ready", "failed", "superseded") for s in st.values()):
            break
        time.sleep(0.1)
    assert st[pv3.id] == "ready"
    assert all(s in ("ready", "superseded") for s in st.values())
    assert db.query(PlanVersion).filter(PlanVersion.status.in_(["pending", "running"])).count() == 0


def test_sse_stream(db, client):
    a = first_plan(db)
    with client.stream("GET", f"/api/plans/{a.id}/events") as r:
        text = "".join(r.iter_text())
    assert "event: ready" in text and "stage_done" in text


def test_diff_text(db, client):
    first_plan(db)
    sc = scenario(db)
    for v in db.query(Vehicle).filter(Vehicle.scenario_id == sc.id).limit(2):
        v.out_of_service = True
    db.commit()
    b = request_recompute(db, sc, "fleet_changed", sync=True)
    d = client.get(f"/api/plans/{b.id}/diff").json()
    assert d["against"] is not None and isinstance(d["text"], str) and d["routes_changed"] >= 1


def test_restart_resumes_interrupted_plans_and_fails_open_simulations(db):
    from salubri_api.models import SimRun
    from salubri_api.services.plan.recovery import resume_interrupted

    pv = first_plan(db)
    sc = scenario(db)
    stuck = PlanVersion(scenario_id=sc.id, version=pv.version + 1, event_kind="manual", status="running")
    db.add(stuck)
    run = SimRun(plan_version_id=pv.id, seed=1, horizon_days=30, replications=2, status="running")
    db.add(run)
    db.commit()
    assert resume_interrupted(sync=True) == [str(sc.id)]
    db.expire_all()
    assert db.get(PlanVersion, stuck.id).status == "ready"
    assert db.get(SimRun, run.id).status == "failed"
