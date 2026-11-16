# SPDX-License-Identifier: AGPL-3.0-or-later


def test_health_reports_db_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["db"] == "ok"
    assert body["osrm"] in ("ok", "down")


def test_problem_json_on_404(client):
    r = client.get("/api/reports/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["status"] == 404


def test_openapi_lists_core_routes(client):
    paths = client.get("/api/openapi.json").json()["paths"]
    for p in (
        "/api/reports",
        "/api/imports",
        "/api/scenarios/{scenario_id}",
        "/api/plans/{plan_id}/events",
        "/api/export/osm",
        "/api/validation/rules",
    ):
        assert p in paths
