# SPDX-License-Identifier: AGPL-3.0-or-later
import io
import json
import zipfile

from conftest import free_point, jpeg


def test_csv_with_french_synonyms_and_errors(client, world):
    p1, p2 = free_point(world, n=1), free_point(world, n=2)
    csv = (
        "lat;lon;type;volume;date;commentaire;device_id\n"
        f"{p1[1]};{p1[0]};plastique;charrette;14/11/2026 10:00;;j1\n"
        f"{p2[1]};{p2[0]};gravats;camion;2026-11-14T11:00:00Z;;j2\n"
        ";;plastique;sac;14/11/2026 10:00;sans coordonnées;j3\n"
        f"{p2[1]};{p2[0]};mixte;sac;31/02/2026;date impossible;j4\n"
    )
    r = client.post("/api/imports", files={"file": ("jury.csv", csv.encode(), "text/csv")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rows_total"] == 4 and body["accepted"] == 2 and body["rejected"] == 2
    rejected = [row for row in body["report"] if row["status"] == "rejected"]
    assert "Coordonnées manquantes" in rejected[0]["errors"][0]
    assert "Date invalide" in rejected[1]["errors"][0]
    ok = [row for row in body["report"] if row["status"] == "accepted"]
    assert ok[0]["score"] is not None and ok[0]["report_status"] in ("probable", "to_review", "verified")


def test_geojson_swapped_coordinates_warning(client, world):
    p = free_point(world, n=3)
    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [p[1], p[0]]},
                "properties": {"waste_type": "household", "external_id": "sw"},
            }
        ],
    }
    body = client.post("/api/imports", files={"file": ("x.geojson", json.dumps(fc).encode())}).json()
    assert body["accepted"] == 1 and any("coords_swapped" in w for w in body["report"][0]["warnings"])
    assert body["report"][0]["report_status"] != "rejected"


def test_dry_run_persists_nothing(client, world):
    p = free_point(world, n=4)
    fc = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": list(p)}, "properties": {}}],
    }
    body = client.post(
        "/api/imports", data={"dry_run": "true"}, files={"file": ("x.geojson", json.dumps(fc).encode())}
    ).json()
    assert body["dry_run"] and body["accepted"] == 1 and body["batch_id"] is None
    assert client.get("/api/reports").json()["total"] == 0


def test_zip_with_photos_and_rollback(client, world):
    p1, p2 = free_point(world, n=5), free_point(world, n=600)
    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": list(p1)},
                "properties": {"photo": "a.jpg", "device_id": "z1"},
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": list(p2)},
                "properties": {"photo": "photos/a.jpg", "device_id": "z2"},
            },
        ],
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("jury.geojson", json.dumps(fc))
        z.writestr("photos/a.jpg", jpeg(77))
    body = client.post("/api/imports", files={"file": ("jury.zip", buf.getvalue(), "application/zip")}).json()
    assert body["accepted"] == 2
    second = body["report"][1]
    assert any(h["rule"] == "R2" for h in second["rule_hits"])  # same photo twice in the jury file
    assert client.get("/api/reports").json()["total"] == 2
    rb = client.post(f"/api/imports/{body['batch_id']}/rollback").json()
    assert rb["reverted"] == 2 and client.get("/api/reports").json()["total"] == 0


def test_bad_file_is_422(client):
    r = client.post("/api/imports", files={"file": ("x.geojson", b"{not json")})
    assert r.status_code == 422 and r.json()["title"] == "Données invalides"
