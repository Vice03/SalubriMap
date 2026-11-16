# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration: reports through the API, rules backed by real PostGIS queries."""

from shapely.geometry import box

from conftest import NOW, Q1, free_point, jpeg, offset, png_small, post_report


def rules(r):  # type: ignore[no-untyped-def]
    return {h["rule"] for h in r["rule_hits"]}


def test_legit_report_is_probable(client, world):
    r = post_report(client, free_point(world), jpeg(1))
    assert r["status"] == "probable" and r["score"] == 100, r


def test_same_photo_twice_is_r2(client, world):
    post_report(client, free_point(world, n=0), jpeg(2))
    r = post_report(client, free_point(world, n=900), jpeg(2), device_id="dev-2", at=NOW.replace(hour=15))
    assert "R2" in rules(r) and r["score"] <= 30


def test_point_inside_building_is_r6(client, world):
    b = next(b for b in world.buildings if Q1.contains(box(*b).centroid) and (b[2] - b[0]) > 0.0001)
    c = box(*b).centroid
    r = post_report(client, (round(c.x, 7), round(c.y, 7)), jpeg(3))
    assert "R6" in rules(r)


def test_point_in_reservoir_is_rejected(client, world):
    res = world.water[1][0].centroid
    r = post_report(client, (round(res.x, 7) + 1e-7, round(res.y, 7) + 1e-7), jpeg(4))
    assert r["status"] == "rejected" and "R7" in rules(r)


def test_out_of_zone_is_rejected(client):
    r = post_report(client, (-4.2967123, 11.1771456), jpeg(5))  # Bobo-Dioulasso
    assert r["status"] == "rejected" and "R5" in rules(r)


def test_zero_zero_rejected(client):
    r = post_report(client, (0.0, 0.0), jpeg(6))
    assert r["status"] == "rejected" and "R8" in rules(r)


def test_impossible_speed_r9(client, world, hours):
    post_report(client, free_point(world, n=0), jpeg(7), device_id="fast")
    r = post_report(client, free_point(world, n=30000), jpeg(8), device_id="fast", at=hours(0.01))
    assert "R9" in rules(r)


def test_spam_r10_and_throttle(client, world, hours):
    last = None
    for i in range(12):
        last = post_report(client, free_point(world, n=i * 400), jpeg(100 + i), device_id="spammer", at=hours(i * 0.08))
    assert "R10" in rules(last)


def test_small_photo_r11(client, world):
    r = post_report(client, free_point(world, n=5), png_small())
    assert "R11" in rules(r)


def test_corroboration_promotes_to_verified(client, world, hours):
    p = free_point(world, n=50)
    a = post_report(client, p, jpeg(20), device_id="A")
    b = post_report(client, offset(p, 6, 4), jpeg(21), device_id="B", at=hours(3))
    assert b["status"] == "verified"
    assert client.get(f"/api/reports/{a['id']}").json()["properties"]["status"] == "verified"
    sites = client.get("/api/dump-sites").json()["features"]
    assert len(sites) == 1 and sites[0]["properties"]["n_reports"] == 2


def test_duplicate_same_device_r1(client, world, hours):
    p = free_point(world, n=70)
    first = post_report(client, p, jpeg(30), device_id="same")
    r = post_report(client, offset(p, 8, 0), jpeg(31), device_id="same", at=hours(5))
    assert "R1" in rules(r) and r["duplicate_of"] == first["id"]


def test_revalidate_is_stable(client, world, hours):
    post_report(client, free_point(world, n=0), jpeg(40))
    r = post_report(client, free_point(world, n=900), jpeg(40), device_id="dev-9", at=hours(2))
    again = client.post(f"/api/reports/{r['id']}/revalidate").json()["properties"]
    assert again["score"] == r["score"] and again["status"] == r["status"]


def test_moderation_patch_forces_status_and_audits(client, world):
    r = post_report(client, free_point(world, n=10), jpeg(50))
    out = client.patch(f"/api/reports/{r['id']}", json={"status": "verified", "note": "vu sur place"}).json()
    assert out["properties"]["status"] == "verified" and out["properties"]["forced_status"]
    assert any(a["action"] == "moderate" for a in client.get("/api/audit").json())
    assert len(client.get("/api/dump-sites").json()["features"]) == 1


def test_rules_endpoint(client):
    body = client.get("/api/validation/rules").json()
    assert [r["code"] for r in body["rules"]] == [f"R{i}" for i in range(1, 13)]
