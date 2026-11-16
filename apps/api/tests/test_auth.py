# SPDX-License-Identifier: AGPL-3.0-or-later
from fastapi.testclient import TestClient


def test_writes_need_mairie_code_but_citizens_can_report(client, world):  # type: ignore[no-untyped-def]
    from conftest import free_point
    from salubri_api.main import app

    anon = TestClient(app)
    sid = anon.get("/api/scenarios").json()[0]["id"]
    assert anon.get(f"/api/scenarios/{sid}").status_code == 200  # lecture publique
    r = anon.post(f"/api/scenarios/{sid}/recompute", json={})
    assert r.status_code == 401
    assert anon.post(f"/api/scenarios/{sid}/recompute", json={}, headers={"X-Salubri-Token": "faux"}).status_code == 401
    assert anon.post("/api/imports", files={"file": ("x.csv", b"lat,lon\n", "text/csv")}).status_code == 401
    lon, lat = free_point(world, n=21)
    sent = anon.post(
        "/api/reports", data={"lat": f"{lat:.7f}", "lon": f"{lon:.7f}", "client_id": "auth-test-1", "device_id": "d1"}
    )
    assert sent.status_code == 201, sent.text  # le citoyen n'a pas besoin de code
    rid = sent.json()["id"]
    assert anon.patch(f"/api/reports/{rid}", json={"status": "verified"}).status_code == 401
    assert client.post(f"/api/scenarios/{sid}/recompute", json={}).status_code == 200  # avec le code
