# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path

from sqlalchemy import text

from salubri_api.models import Commune
from salubri_api.seed.load_osm import load_osm
from salubri_api.seed.run import seed

OSM = """<?xml version='1.0' encoding='UTF-8'?>
<osm version="0.6">
 <node id="1" lat="12.35" lon="-1.53"/><node id="2" lat="12.35" lon="-1.51"/>
 <node id="3" lat="12.36" lon="-1.53"/><node id="4" lat="12.36" lon="-1.52"/><node id="5" lat="12.37" lon="-1.52"/>
 <node id="6" lat="12.361" lon="-1.521"><tag k="amenity" v="hospital"/><tag k="name" v="CHU test"/></node>
 <node id="10" lat="12.340" lon="-1.540"/><node id="11" lat="12.340" lon="-1.535"/>
 <node id="12" lat="12.345" lon="-1.535"/><node id="13" lat="12.345" lon="-1.540"/>
 <way id="100"><nd ref="1"/><nd ref="2"/><tag k="highway" v="primary"/></way>
 <way id="101"><nd ref="3"/><nd ref="4"/><nd ref="5"/><tag k="waterway" v="river"/></way>
 <way id="102"><nd ref="10"/><nd ref="11"/><nd ref="12"/><nd ref="13"/><nd ref="10"/><tag k="natural" v="water"/></way>
 <way id="103"><nd ref="3"/><nd ref="5"/><tag k="highway" v="footway"/></way>
</osm>"""


def test_load_osm_from_xml(db, tmp_path: Path):
    f = tmp_path / "mini.osm"
    f.write_text(OSM)
    c = db.query(Commune).first()
    db.execute(text("DELETE FROM roads; DELETE FROM water; DELETE FROM pois"))
    out = load_osm(db, c.id, f)
    db.commit()
    assert out == {"roads": 2, "water": 2, "pois": 1}
    assert db.execute(text("SELECT count(*) FROM roads WHERE truck_ok")).scalar_one() == 1
    assert db.execute(text("SELECT area_m2 FROM water WHERE kind = 'water'")).scalar_one() > 100_000


def test_seed_synthetic_city_is_idempotent(db):
    first = seed("ouagadougou", force=True, reports=False, plans=False)
    assert first["counts"]["quartiers"] >= 24 and first["counts"]["buildings"] > 10_000 and first["ilots"] > 500
    again = seed("ouagadougou", force=False, reports=False, plans=False)
    assert again.get("skipped") is True
