# SPDX-License-Identifier: AGPL-3.0-or-later
"""Commune, quartiers, synthetic world, vehicles and scenarios from data/communes/<slug>/."""

import csv
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from shapely.geometry import MultiPolygon, Point, box
from shapely.geometry import shape as geo_shape
from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api.models import Commune, Poi, Quartier, Road, Scenario, Vehicle, Water
from salubri_api.seed.synthetic import World, build_world
from salubri_api.services.geo import to_wkb
from salubri_api.services.params import ScenarioParams

log = logging.getLogger("salubri.seed")


def load_commune(s: Session, folder: Path) -> Commune:
    meta = json.loads((folder / "commune.json").read_text(encoding="utf-8"))
    params = json.loads((folder / "params_default.json").read_text(encoding="utf-8"))
    x0, y0, x1, y1 = meta["bbox"]
    c = Commune(
        slug=meta["slug"],
        name=meta["name"],
        bbox=to_wkb(box(x0, y0, x1, y1)),
        depot_geom=to_wkb(Point(*meta["depot"])),
        params_default=params,
    )
    s.add(c)
    s.flush()
    return c


def load_quartiers(s: Session, commune: Commune, folder: Path) -> list[Quartier]:
    fc = json.loads((folder / "quartiers.geojson").read_text(encoding="utf-8"))
    out = []
    for f in fc["features"]:
        g = geo_shape(f["geometry"])
        if g.geom_type == "Polygon":
            g = MultiPolygon([g])
        p = f.get("properties", {})
        q = Quartier(
            commune_id=commune.id,
            name=p["name"],
            arrondissement=p.get("arrondissement"),
            population=int(p.get("population", 0)),
            geom=to_wkb(g),
            source=p.get("source", "demo"),
        )
        s.add(q)
        out.append(q)
    s.flush()
    return out


def insert_world(
    s: Session, commune_id: uuid.UUID, w: World, roads: bool, water: bool, buildings: bool
) -> dict[str, int]:
    out = {"roads": 0, "water": 0, "pois": 0, "buildings": 0}
    if roads:
        for g, hw, surf, ok in w.roads:
            s.add(Road(commune_id=commune_id, geom=to_wkb(g), highway=hw, surface=surf, truck_ok=ok))
        out["roads"] = len(w.roads)
    if water:
        for g, kind, name, flood in w.water:
            s.add(Water(commune_id=commune_id, geom=to_wkb(g), kind=kind, name=name, flood_prone=flood))
        for g, kind, name in w.pois:
            s.add(Poi(commune_id=commune_id, geom=to_wkb(g), kind=kind, name=name))
        out["water"], out["pois"] = len(w.water), len(w.pois)
    s.flush()
    s.execute(text("UPDATE water SET area_m2 = ST_Area(geom::geography) WHERE commune_id = :c"), {"c": commune_id})
    if buildings and w.buildings:
        cols = list(zip(*w.buildings, strict=True))
        s.execute(
            text("""
            INSERT INTO buildings (id, commune_id, geom, area_m2, confidence, source)
            SELECT gen_random_uuid(), :c, g, ST_Area(g::geography), 0.9, 'synthetic'
            FROM (SELECT ST_MakeEnvelope(x0, y0, x1, y1, 4326) AS g
                  FROM unnest(CAST(:x0 AS float8[]), CAST(:y0 AS float8[]), CAST(:x1 AS float8[]), CAST(:y1 AS float8[]))
                       AS t(x0, y0, x1, y1)) z"""),
            {"c": commune_id, "x0": list(cols[0]), "y0": list(cols[1]), "x1": list(cols[2]), "y1": list(cols[3])},
        )
        out["buildings"] = len(w.buildings)
    return out


def synthetic_world_for(commune_json: dict[str, Any], quartiers_fc: dict[str, Any]) -> World:
    qs = [
        (f["properties"]["name"], geo_shape(f["geometry"]), int(f["properties"].get("population", 0)))
        for f in quartiers_fc["features"]
    ]
    return build_world(tuple(commune_json["bbox"]), qs)  # type: ignore[arg-type]


def load_vehicles_and_scenarios(
    s: Session, commune: Commune, folder: Path, quartiers: list[Quartier]
) -> list[Scenario]:
    meta = json.loads((folder / "commune.json").read_text(encoding="utf-8"))
    base_params = ScenarioParams(**{k: v for k, v in commune.params_default.items() if k != "validation"})
    with (folder / "vehicles.csv").open(encoding="utf-8") as fh:
        vehicles = list(csv.DictReader(fh))
    by_name = {q.name: q for q in quartiers}
    scenarios = []
    for spec in meta.get("scenarios", [{"name": "Base", "baseline": True}]):
        ids = None
        if spec.get("quartiers"):
            ids = [str(by_name[n].id) for n in spec["quartiers"] if n in by_name]
        p = base_params.model_copy(update={"active_quartier_ids": ids, **spec.get("params", {})})
        sc = Scenario(
            commune_id=commune.id,
            name=spec["name"],
            params=p.model_dump(mode="json"),
            is_baseline=bool(spec.get("baseline")),
        )
        s.add(sc)
        s.flush()
        for v in vehicles:
            s.add(
                Vehicle(
                    scenario_id=sc.id,
                    label=v["label"],
                    kind=v["kind"],
                    capacity_t=float(v["capacity_t"]),
                    cost_per_km=float(v["cost_per_km"]),
                    fixed_cost_day=float(v["fixed_cost_day"]),
                    shift_start=int(v.get("shift_start") or 300),
                    shift_end=int(v.get("shift_end") or 1080),
                )
            )
        scenarios.append(sc)
    s.flush()
    return scenarios
