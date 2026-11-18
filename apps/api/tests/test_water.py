# SPDX-License-Identifier: AGPL-3.0-or-later
"""Retenues d'eau et dépotoirs qui les menacent (carte : couche « Retenues d'eau »)."""

from conftest import jpeg, offset, post_report


def test_retenues_and_dumps_near_them(client, world, hours):  # type: ignore[no-untyped-def]
    fc = client.get("/api/eau").json()
    assert len(fc["features"]) == 3 and fc["features"][0]["properties"]["surface_ha"] > 0.5
    assert fc["features"][0]["properties"]["nom"].startswith("Barrage")
    barrage = world.water[1][0]
    xs, ys = barrage.exterior.xy
    i = max(range(len(ys)), key=lambda k: ys[k])
    p = offset((xs[i], ys[i]), 0, 60)  # 60 m au nord de la rive
    post_report(client, p, jpeg(31), device_id="A")
    post_report(client, offset(p, 4, 2), jpeg(32), device_id="B", at=hours(2))
    near = client.get("/api/eau/depotoirs", params={"distance_m": 150}).json()
    assert len(near["sites"]) == 1 and 40 <= near["sites"][0]["distance_m"] <= 90
    assert near["sites"][0]["retenue"].startswith("Barrage") and near["retenues"][0]["depotoirs"] == 1
    assert client.get("/api/eau/depotoirs", params={"distance_m": 20}).json()["sites"] == []
    assert client.get("/api/eau/depotoirs", params={"distance_m": 5}).status_code == 422
