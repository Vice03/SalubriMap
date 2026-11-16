# SPDX-License-Identifier: AGPL-3.0-or-later
from conftest import free_point, jpeg, post_report


def test_idempotent_client_id(client, world):
    p = free_point(world, n=11)
    a = post_report(client, p, jpeg(1), client_id="c-123")
    data = {"lon": str(p[0]), "lat": str(p[1]), "client_id": "c-123"}
    r = client.post("/api/reports", data=data)
    assert r.status_code == 200 and r.json()["id"] == a["id"] and r.json()["already_received"]
    assert client.get("/api/reports").json()["total"] == 1


def test_filters(client, world):
    post_report(client, free_point(world, n=12), jpeg(2), waste_type="plastic")
    post_report(client, (-4.29, 11.17), jpeg(3), device_id="x")  # rejected R5
    fc = client.get("/api/reports", params={"status": "rejected"}).json()
    assert fc["total"] == 1 and fc["features"][0]["properties"]["status"] == "rejected"
    assert client.get("/api/reports", params={"rule": "R5"}).json()["total"] == 1
    assert client.get("/api/reports", params={"type": "plastic"}).json()["total"] == 1
    assert client.get("/api/reports", params={"bbox": "-1.56,12.33,-1.50,12.38"}).json()["total"] == 1
    feat = client.get("/api/reports", params={"type": "plastic"}).json()["features"][0]
    assert feat["properties"]["photo_url"].startswith("/photos/")
    assert client.get(feat["properties"]["photo_url"]).status_code == 200


def test_stats(client, world):
    post_report(client, free_point(world, n=13), jpeg(4))
    st = client.get("/api/reports/stats").json()
    assert st["total"] == 1 and st["by_status"]["probable"] == 1


def test_invalid_waste_type_422(client):
    r = client.post("/api/reports", data={"lon": "-1.52", "lat": "12.35", "waste_type": "nuclear"})
    assert r.status_code == 422


def test_unreadable_photo_422(client):
    r = client.post(
        "/api/reports", data={"lon": "-1.52", "lat": "12.35"}, files={"photo": ("p.jpg", b"not an image", "image/jpeg")}
    )
    assert r.status_code == 422
