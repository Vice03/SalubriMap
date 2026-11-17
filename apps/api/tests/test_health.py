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


def test_version_in_sync_and_health_details(client):  # type: ignore[no-untyped-def]
    """Lot F : version unique (pyproject = __version__), carte et file de recalculs dans /api/health."""
    import tomllib
    from pathlib import Path

    from salubri_api import __version__

    py = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())["project"]["version"]
    assert py == __version__
    h = client.get("/api/health").json()
    assert h["version"] == __version__ and set(h["queue"]) >= {"debounced", "pending", "running"}


def test_request_id_and_json_logs(client, caplog):  # type: ignore[no-untyped-def]
    import json
    import logging

    from salubri_api.logs import JsonFormatter

    r = client.get("/api/communes/ouagadougou", headers={"X-Request-ID": "essai-123"})
    assert r.headers["X-Request-ID"] == "essai-123"
    assert client.get("/api/communes/ouagadougou").headers["X-Request-ID"]  # créé s'il manque
    rec = logging.LogRecord("salubri.test", logging.INFO, __file__, 1, "bonjour %s", ("Ouaga",), None)
    line = json.loads(JsonFormatter().format(rec))
    assert line["message"] == "bonjour Ouaga" and line["niveau"] == "INFO" and "requete" in line


def test_audit_pagination(client):  # type: ignore[no-untyped-def]
    first = client.get("/api/audit", params={"limit": 2}).json()
    second = client.get("/api/audit", params={"limit": 2, "offset": 2}).json()
    assert not {a["id"] for a in first} & {a["id"] for a in second}
