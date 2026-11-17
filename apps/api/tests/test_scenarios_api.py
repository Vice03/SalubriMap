# SPDX-License-Identifier: AGPL-3.0-or-later
import time


def wait(client, plan_id, timeout=20):  # type: ignore[no-untyped-def]
    t0 = time.time()
    while time.time() - t0 < timeout:
        p = client.get(f"/api/plans/{plan_id}").json()
        if p["status"] in ("ready", "failed"):
            return p
        if p["status"] == "superseded":
            plan_id = client.get(f"/api/scenarios/{p['scenario_id']}").json()["latest_plan_id"]
        time.sleep(0.1)
    raise AssertionError("timeout")


def test_patch_params_maps_to_event(client):
    sc = client.get("/api/scenarios").json()[0]
    r = client.patch(f"/api/scenarios/{sc['id']}", json={"params": {"budget_fcfa_month": 10_000_000}}).json()
    assert r["event"] == "budget_changed"
    r = client.patch(
        f"/api/scenarios/{sc['id']}", json={"params": {"season": "rain", "budget_fcfa_month": 9_000_000}}
    ).json()
    assert r["event"] == "season_changed"
    assert wait(client, r["plan_version_id"])["status"] == "ready"


def test_invalid_param_422(client):
    sc = client.get("/api/scenarios").json()[0]
    r = client.patch(f"/api/scenarios/{sc['id']}", json={"params": {"subscription_rate": 3}})
    assert r.status_code == 422


def test_clone_breakdown_compare(client):
    base = client.get("/api/scenarios").json()[0]
    wait(client, client.post(f"/api/scenarios/{base['id']}/recompute").json()["plan_version_id"])
    b = client.post("/api/scenarios", json={"name": "B", "parent_id": base["id"]}).json()
    wait(client, b["plan_version_id"])
    vid = b["vehicles"][-1]["id"]
    r = client.post(f"/api/scenarios/{b['id']}/vehicles/{vid}/breakdown", json={"out_of_service": True}).json()
    assert wait(client, r["plan_version_id"])["status"] == "ready"
    cmp = client.get("/api/scenarios/compare", params={"a": base["id"], "b": b["id"]}).json()
    assert cmp["a"]["summary"]["vehicles_available"] == 4 and cmp["b"]["summary"]["vehicles_available"] == 3
    assert "km_day" in cmp["delta"] and "sim.wild_dump_t" in cmp["delta"]
    assert client.delete(f"/api/scenarios/{b['id']}").status_code == 204
    assert client.delete(f"/api/scenarios/{base['id']}").status_code == 409


def test_params_schema_has_french_labels(client):
    sch = client.get("/api/scenarios/params-schema").json()
    assert sch["properties"]["season"]["label"] == "Saison"
    assert sch["properties"]["budget_fcfa_month"]["event"] == "budget_changed"


def test_replications(client):
    base = client.get("/api/scenarios").json()[0]
    pv = wait(client, client.post(f"/api/scenarios/{base['id']}/recompute").json()["plan_version_id"])
    run = client.post(f"/api/plans/{pv['id']}/simulate", json={"replications": 3}).json()
    for _ in range(100):
        out = client.get(f"/api/sim-runs/{run['sim_run_id']}").json()
        if out["status"] in ("ready", "failed"):
            break
        time.sleep(0.1)
    assert out["status"] == "ready", out
    m = out["metrics_summary"]["collected_t"]
    assert m["p10"] <= m["median"] <= m["p90"]
    assert m["p5"] <= m["p10"] and m["p90"] <= m["p95"]  # intervalle à 90 %
    assert "households" in out["metrics_summary"]  # modèle à agents par défaut


def test_replications_mode_agrege(client):
    base = client.get("/api/scenarios").json()[0]
    pv = wait(client, client.post(f"/api/scenarios/{base['id']}/recompute").json()["plan_version_id"])
    assert pv["summary"]["sim"]["households"] > 0  # E6 tourne aussi en mode agents
    run = client.post(f"/api/plans/{pv['id']}/simulate", json={"replications": 2, "mode": "agrege"}).json()
    for _ in range(100):
        out = client.get(f"/api/sim-runs/{run['sim_run_id']}").json()
        if out["status"] in ("ready", "failed"):
            break
        time.sleep(0.1)
    assert out["status"] == "ready", out
    assert "households" not in out["metrics_summary"]
    bad = client.post(f"/api/plans/{pv['id']}/simulate", json={"mode": "autre"})
    assert bad.status_code == 422


def test_add_and_remove_vehicle(client):
    sc = client.get("/api/scenarios").json()[0]
    n = len(sc["vehicles"])
    r = client.post(f"/api/scenarios/{sc['id']}/vehicles", json={"kind": "truck_12t"})
    assert r.status_code == 201, r.text
    v = r.json()["vehicle"]
    assert v["capacity_t"] == 12 and v["label"].startswith("BF-")
    assert len(client.get(f"/api/scenarios/{sc['id']}").json()["vehicles"]) == n + 1
    assert client.delete(f"/api/scenarios/{sc['id']}/vehicles/{v['id']}").status_code == 200
    assert len(client.get(f"/api/scenarios/{sc['id']}").json()["vehicles"]) == n
    assert client.delete(f"/api/scenarios/{sc['id']}/vehicles/{v['id']}").status_code == 404
    assert "truck_8t" in client.get("/api/scenarios/meta/vehicle-kinds").json()
