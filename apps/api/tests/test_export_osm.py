# SPDX-License-Identifier: AGPL-3.0-or-later
import xml.etree.ElementTree as ET

from conftest import free_point, jpeg, offset, post_report


def _verified_site(client, world, hours):  # type: ignore[no-untyped-def]
    p = free_point(world, n=80)
    post_report(client, p, jpeg(1), device_id="secret-device-A", comment="numéro de téléphone 70 00 00 00")
    post_report(client, offset(p, 4, 4), jpeg(2), device_id="secret-device-B", at=hours(4))


def test_osm_xml_valid_and_anonymous(client, world, hours):
    _verified_site(client, world, hours)
    r = client.get("/api/export/osm")
    assert r.status_code == 200
    root = ET.fromstring(r.content)
    nodes = root.findall("node")
    assert root.tag == "osm" and len(nodes) == 1 and int(nodes[0].get("id")) < 0
    tags = {t.get("k"): t.get("v") for t in nodes[0].findall("tag")}
    assert tags["amenity"] == "waste_dump_site" and tags["source"] == "Salubri;survey"
    assert "waste" in tags and "salubri:id" in tags
    assert b"secret-device" not in r.content and "téléphone".encode() not in r.content


def test_csv_and_geojson_exports(client, world, hours):
    _verified_site(client, world, hours)
    csv = client.get("/api/export/csv")
    assert csv.text.startswith("﻿id;lat;lon") and "secret-device" not in csv.text
    gj = client.get("/api/export/geojson").json()
    assert gj["type"] == "FeatureCollection" and len(gj["features"]) == 1 and gj["license"] == "CC0-1.0"


def test_osc_essai_cree_seulement_les_nouveaux(client, world, hours):
    _verified_site(client, world, hours)
    r = client.get("/api/export/osc")
    assert r.status_code == 200
    root = ET.fromstring(r.content)
    nodes = root.find("create").findall("node")
    assert root.tag == "osmChange" and len(nodes) == 1 and int(nodes[0].get("id")) < 0
    tags = {t.get("k"): t.get("v") for t in nodes[0].findall("tag")}
    assert tags["amenity"] == "waste_dump_site" and b"secret-device" not in r.content
    site = client.get("/api/dump-sites").json()
    sid = (site["features"] if isinstance(site, dict) else site)[0]
    sid = sid.get("id") or sid["properties"]["id"]
    assert client.patch(f"/api/dump-sites/{sid}", json={"osm_id": 123456}).status_code == 200
    again = ET.fromstring(client.get("/api/export/osc").content)
    assert again.find("create").findall("node") == []  # déjà versé : rien à créer
