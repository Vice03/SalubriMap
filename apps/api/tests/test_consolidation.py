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
