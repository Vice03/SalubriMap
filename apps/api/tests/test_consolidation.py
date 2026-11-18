# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from datetime import UTC, datetime, timedelta

from conftest import free_point, jpeg, offset, post_report
from salubri_api.services.consolidation import cluster_reports, priority

T = datetime(2026, 11, 1, tzinfo=UTC)


def test_cluster_pure():
    rows = [
        (uuid.uuid4(), 12.35, -1.52, "plastic", "cart", T, 100),
        (uuid.uuid4(), 12.35010, -1.52005, "plastic", "truck", T + timedelta(days=1), 90),
        (uuid.uuid4(), 12.36, -1.52, "rubble", "bag", T, 100),
    ]
    cl = cluster_reports(rows, 30)
    assert len(cl) == 2
    big = max(cl, key=lambda c: len(c.report_ids))
    assert len(big.report_ids) == 2 and big.volume_m3 == 6.0 and big.dominant_type == "plastic"


def test_priority_grows_with_water_and_age():
    now = T + timedelta(days=30)
    assert priority(1, True, T, now) > priority(1, False, T, now) > priority(1, False, now, now)


def test_cleaned_then_recurring(client, world, hours):
    p = free_point(world, n=60)
    post_report(client, p, jpeg(1), device_id="A")
    post_report(client, offset(p, 5, 0), jpeg(2), device_id="B", at=hours(2))
    site = client.get("/api/dump-sites").json()["features"][0]["properties"]
    assert site["status"] == "active"
    out = client.post(f"/api/dump-sites/{site['id']}/cleaned", data={"device_id": "laabal-1"}).json()
    assert out["properties"]["status"] == "cleaned"
    # it comes back: two new independent reports after the cleaning
    from salubri_api.models import utcnow

    t = utcnow()
    post_report(client, offset(p, 3, 3), jpeg(3), device_id="C", at=t + timedelta(hours=1))
    post_report(client, offset(p, -3, 2), jpeg(4), device_id="D", at=t + timedelta(hours=3))
    sites = client.get("/api/dump-sites").json()["features"]
    assert len(sites) == 1 and sites[0]["properties"]["status"] == "recurring"
    assert sites[0]["properties"]["id"] == site["id"]


def test_dump_in_a_drain_is_not_penalised_and_is_prioritised(client, db, world, hours):  # type: ignore[no-untyped-def]
    """Caniveau OSM (waterway=drain) à 3 m : la règle R7 ne pénalise pas, le dépotoir est marqué et passe en tête."""
    from shapely.geometry import LineString
    from sqlalchemy import text

    from salubri_api.models import Commune
    from salubri_api.models.buildings import Water
    from salubri_api.services.geo import to_wkb

    p = free_point(world, n=70)
    q = free_point(world, n=75)
    cid = db.query(Commune).first().id
    a, b = offset(p, -40, 3), offset(p, 40, 3)
    db.add(Water(commune_id=cid, geom=to_wkb(LineString([a, b])), kind="waterway", subkind="drain", name="Caniveau"))
    db.commit()
    r = post_report(client, p, jpeg(11), device_id="A")
    assert r["score"] == 100 and not r["rule_hits"], r  # pas de « R7 dans l'eau » pour un caniveau
    post_report(client, offset(p, 4, -2), jpeg(12), device_id="B", at=hours(2))
    post_report(client, q, jpeg(13), device_id="C")
    post_report(client, offset(q, 4, -2), jpeg(14), device_id="D", at=hours(2))
    sites = {f["properties"]["id"]: f["properties"] for f in client.get("/api/dump-sites").json()["features"]}
    drain = next(s for s in sites.values() if s["near_drain"])
    other = next(s for s in sites.values() if not s["near_drain"])
    assert drain["near_water"] and drain["priority"] > other["priority"] * 1.2
    assert db.execute(text("SELECT count(*) FROM water WHERE subkind = 'drain'")).scalar() == 1


def test_recurring_dump_goes_to_laabal_once(client, world, hours):  # type: ignore[no-untyped-def]
    from salubri_api.models import utcnow

    p = free_point(world, n=80)
    post_report(client, p, jpeg(21), device_id="A")
    post_report(client, offset(p, 5, 0), jpeg(22), device_id="B", at=hours(2))
    site = client.get("/api/dump-sites").json()["features"][0]["properties"]
    assert client.get("/api/dump-sites/laabal/alertes").json()["zones"] == []
    client.post(f"/api/dump-sites/{site['id']}/cleaned", data={"device_id": "st-1"})
    t = utcnow()
    post_report(client, offset(p, 3, 3), jpeg(23), device_id="C", at=t + timedelta(hours=1))
    post_report(client, offset(p, -3, 2), jpeg(24), device_id="D", at=t + timedelta(hours=3))
    post_report(client, offset(p, 1, -2), jpeg(25), device_id="E", at=t + timedelta(hours=5))  # re-consolidation
    al = client.get("/api/dump-sites/laabal/alertes").json()
    assert al["numero"] == "+22600000000" and al["numero_demo"] and al["auto"]
    (z,) = al["zones"]
    assert z["niveau"] == "alerte" and z["recidivistes"] == 1 and z["sites"][0]["auto"] and z["sites"][0]["transmis_le"]
    journal = client.get("/api/audit", params={"action": "laabal_alert"}).json()
    rows = journal if isinstance(journal, list) else journal.get("items", journal.get("entries", []))
    assert sum(1 for e in rows if e.get("action") == "laabal_alert" and e.get("actor") == "auto") == 1
