# SPDX-License-Identifier: AGPL-3.0-or-later
"""Load water, roads and points of interest from an OSM extract (.osm.pbf or .osm) with pyosmium."""

import logging
import uuid
from pathlib import Path

import osmium
from shapely import wkb
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api.models import Poi, Road, Water
from salubri_api.services.geo import to_wkb

log = logging.getLogger("salubri.seed")

WATERWAYS = {"river", "stream", "canal", "drain", "ditch"}
TRUCK_HIGHWAYS = {
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "unclassified",
    "residential",
    "living_street",
    "service",
    "motorway_link",
    "trunk_link",
    "primary_link",
    "secondary_link",
    "tertiary_link",
}
OTHER_HIGHWAYS = {"track", "path", "footway", "pedestrian", "steps", "cycleway"}
AMENITY_POI = {
    "hospital": "hospital",
    "clinic": "clinic",
    "doctors": "doctors",
    "school": "school",
    "marketplace": "marketplace",
}
LANDUSE_POI = {"cemetery": "cemetery", "military": "military"}


class _Handler(osmium.SimpleHandler):
    def __init__(self) -> None:
        super().__init__()
        self.f = osmium.geom.WKBFactory()
        self.roads: list[tuple[BaseGeometry, str, str | None, bool, int]] = []
        self.water: list[tuple[BaseGeometry, str, str | None]] = []
        self.pois: list[tuple[BaseGeometry, str, str | None]] = []

    def node(self, n: osmium.osm.Node) -> None:
        kind = AMENITY_POI.get(n.tags.get("amenity", ""))
        if kind:
            self.pois.append((wkb.loads(self.f.create_point(n), hex=True), kind, n.tags.get("name")))

    def way(self, w: osmium.osm.Way) -> None:
        try:
            hw = w.tags.get("highway")
            if hw in TRUCK_HIGHWAYS or hw in OTHER_HIGHWAYS:
                g = wkb.loads(self.f.create_linestring(w), hex=True)
                self.roads.append((g, hw, w.tags.get("surface"), hw in TRUCK_HIGHWAYS, w.id))
            ww = w.tags.get("waterway")
            if ww in WATERWAYS:
                self.water.append((wkb.loads(self.f.create_linestring(w), hex=True), "waterway", w.tags.get("name")))
        except Exception:  # broken geometry in the extract: skip it
            pass

    def area(self, a: osmium.osm.Area) -> None:
        try:
            tags = a.tags
            g = None
            if tags.get("natural") == "water" or tags.get("landuse") in ("reservoir", "basin") or tags.get("water"):
                g = wkb.loads(self.f.create_multipolygon(a), hex=True)
                kind = "wetland" if tags.get("natural") == "wetland" else "water"
                for poly in getattr(g, "geoms", [g]):
                    self.water.append((poly, kind, tags.get("name")))
            elif tags.get("natural") == "wetland":
                g = wkb.loads(self.f.create_multipolygon(a), hex=True)
                for poly in getattr(g, "geoms", [g]):
                    self.water.append((poly, "wetland", tags.get("name")))
            kind = AMENITY_POI.get(tags.get("amenity", "")) or LANDUSE_POI.get(tags.get("landuse", ""))
            if kind:
                g = g or wkb.loads(self.f.create_multipolygon(a), hex=True)
                self.pois.append((g, kind, tags.get("name")))
        except Exception:
            pass


def load_osm(s: Session, commune_id: uuid.UUID, path: Path, bbox: Polygon | None = None) -> dict[str, int]:
    h = _Handler()
    h.apply_file(str(path), locations=True)
    keep = (lambda g: g.intersects(bbox)) if bbox is not None else (lambda g: True)
    n_r = n_w = n_p = 0
    for g, hw, surf, ok, oid in h.roads:
        if keep(g):
            s.add(Road(commune_id=commune_id, osm_id=oid, geom=to_wkb(g), highway=hw, surface=surf, truck_ok=ok))
            n_r += 1
    for g, kind, name in h.water:
        if keep(g):
            s.add(
                Water(
                    commune_id=commune_id,
                    geom=to_wkb(g),
                    kind=kind,
                    name=(name or None) and name[:128],
                    flood_prone=kind == "waterway",
                )
            )
            n_w += 1
    for g, kind, name in h.pois:
        if keep(g):
            s.add(Poi(commune_id=commune_id, geom=to_wkb(g), kind=kind, name=(name or None) and name[:128]))
            n_p += 1
    s.flush()
    s.execute(text("UPDATE water SET area_m2 = ST_Area(geom::geography) WHERE commune_id = :c"), {"c": commune_id})
    log.info("OSM : %s voies, %s éléments d'eau, %s POI", n_r, n_w, n_p)
    return {"roads": n_r, "water": n_w, "pois": n_p}
