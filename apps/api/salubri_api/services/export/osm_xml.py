# SPDX-License-Identifier: AGPL-3.0-or-later
"""OSM XML (.osm) for JOSM: negative ids, community-reviewed tags, never any personal data."""

from xml.sax.saxutils import quoteattr

from salubri_api.models import DumpSite
from salubri_api.services.geo import shape

WASTE_OSM = {
    "household": "trash",
    "plastic": "plastic",
    "rubble": "rubble",
    "organic": "organic",
    "medical": "medical",
    "mixed": "mixed",
    "other": "trash",
}


def dump_sites_osm(sites: list[DumpSite]) -> str:
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<osm version="0.6" generator="salubri" upload="never">']
    for i, d in enumerate(sites, start=1):
        g = shape(d.geom)
        tags = {
            "amenity": "waste_dump_site",
            "waste": WASTE_OSM.get(d.dominant_type, "trash"),
            "description": f"Dépotoir sauvage signalé {d.n_reports} fois, volume estimé {d.volume_est_m3:g} m³",
            "survey:date": d.last_reported_at.date().isoformat(),
            "source": "Salubri;survey",
            "salubri:id": str(d.id),
            "salubri:confidence": f"{d.mean_score:.0f}",
        }
        out.append(f'  <node id="-{i}" lat="{g.y:.7f}" lon="{g.x:.7f}" visible="true">')
        for k, v in tags.items():
            out.append(f"    <tag k={quoteattr(k)} v={quoteattr(v)}/>")
        out.append("  </node>")
    out.append("</osm>")
    return "\n".join(out) + "\n"
