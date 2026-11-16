# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate the demo data of data/communes/ouagadougou/ (deterministic, seed 42).

Writes: commune.json, quartiers.geojson, params_default.json, vehicles.csv, reports_demo.geojson,
and the jury examples in data/jury/. Re-run after editing the constants below.

    python scripts/gen_demo_data.py
"""

import csv
import json
import math
from datetime import UTC, datetime, timedelta

import numpy as np
from shapely.geometry import Point, Polygon, box, mapping
from shapely.ops import unary_union
from shapely.strtree import STRtree

from _common import DATA
from salubri_api.seed.synthetic import M_LAT, build_world, m_lon
from salubri_api.services.params import ScenarioParams, ValidationThresholds

SLUG = "ouagadougou"
BBOX = (-1.62, 12.28, -1.42, 12.46)
GRID = (-1.60, 12.30, -1.44, 12.44)
DEPOT = (-1.50, 12.47)  # [HYPOTHÈSE] CTVD de Polesgo, au nord-est : corriger avec la position OSM réelle
ANCHOR = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)
PILOT = "Arrondissement 5 — Nord"
TYPES = ["household", "mixed", "plastic", "organic", "rubble", "medical", "other"]
TYPE_W = [0.40, 0.20, 0.15, 0.12, 0.08, 0.02, 0.03]
VOLUMES = ["bag", "wheelbarrow", "cart", "truck", "more"]
VOL_W = [0.25, 0.30, 0.30, 0.12, 0.03]


def quartiers(rng: np.random.Generator) -> list[dict]:  # type: ignore[type-arg]
    cols, rows = 6, 4
    x0, y0, x1, y1 = GRID
    xs, ys = np.linspace(x0, x1, cols + 1), np.linspace(y0, y1, rows + 1)
    jit = 0.004
    nodes = {
        (i, j): (
            xs[i] + (rng.uniform(-jit, jit) if 0 < i < cols else 0),
            ys[j] + (rng.uniform(-jit, jit) if 0 < j < rows else 0),
        )
        for i in range(cols + 1)
        for j in range(rows + 1)
    }
    feats = []
    k = 0
    for j in range(rows):
        for i in range(cols):
            arr = k // 2 + 1
            name = f"Arrondissement {arr} — {'Nord' if k % 2 == 0 else 'Sud'}"
            ring = [nodes[(i, j)], nodes[(i + 1, j)], nodes[(i + 1, j + 1)], nodes[(i, j + 1)], nodes[(i, j)]]
            pop = int(rng.integers(35_000, 65_000) // 100 * 100)
            feats.append(
                {
                    "type": "Feature",
                    "geometry": mapping(Polygon(ring)),
                    "properties": {"name": name, "arrondissement": arr, "population": pop, "source": "demo"},
                }
            )
            k += 1
    return feats


def main() -> None:
    rng = np.random.default_rng(42)
    folder = DATA / "communes" / SLUG
    folder.mkdir(parents=True, exist_ok=True)
    qf = quartiers(rng)
    (folder / "quartiers.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": qf}, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    commune = {
        "slug": SLUG,
        "name": "Ouagadougou",
        "bbox": list(BBOX),
        "depot": list(DEPOT),
        "depot_name": "CTVD de Polesgo (position à vérifier)",
        "osm_extract": "ouaga.osm.pbf",
        "buildings": "ouaga_buildings.csv.gz",
        "scenarios": [
            {"name": "Zone pilote", "baseline": True, "quartiers": [PILOT]},
            {"name": "Ville entière (démo)", "quartiers": None},
        ],
    }
    (folder / "commune.json").write_text(json.dumps(commune, ensure_ascii=False, indent=2), encoding="utf-8")
    params = ScenarioParams().model_dump(mode="json")
    params.pop("active_quartier_ids")
    params["validation"] = ValidationThresholds().model_dump()
    params["_sources"] = {
        "waste_kg_per_person_day": "≈ 0,6 kg/hab/j, Sidwaya (mairie de Ouagadougou) ; à confirmer avec la mairie",
        "subscription_rate": "[HYPOTHÈSE] 35 %",
        "collection_point_capacity_t": "[HYPOTHÈSE] bac de 6 m³ ≈ 2,5 t",
        "budget_fcfa_month": "[HYPOTHÈSE] à remplacer par le budget fourni par la mairie",
    }
    (folder / "params_default.json").write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")
    with (folder / "vehicles.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["label", "kind", "capacity_t", "cost_per_km", "fixed_cost_day", "shift_start", "shift_end"])
        for i in range(1, 9):
            big = i > 5
            w.writerow(
                [
                    f"BF-{i:02d}",
                    "truck_12t" if big else "truck_8t",
                    12 if big else 8,
                    520 if big else 450,
                    25000 if big else 20000,
                    300,
                    1080,
                ]
            )

    world = build_world(
        BBOX,
        [
            (f["properties"]["name"], Polygon(f["geometry"]["coordinates"][0]), f["properties"]["population"])
            for f in qf
        ],
    )
    btree = STRtree([box(*b) for b in world.buildings])
    river = world.water[0][0]
    wet = unary_union([river.buffer(20 * M_LAT)] + [w[0].buffer(20 * M_LAT) for w in world.water[1:]])
    markets = [p[0].centroid for p in world.pois if p[1] == "marketplace"]
    zone = unary_union([Polygon(f["geometry"]["coordinates"][0]) for f in qf])
    pilot = next(Polygon(f["geometry"]["coordinates"][0]) for f in qf if f["properties"]["name"] == PILOT)

    def ok(p: Point) -> bool:
        return (
            zone.contains(p)
            and not wet.contains(p)
            and not any(
                box(*world.buildings[k]).buffer(3 * M_LAT).contains(p) for k in btree.query(p.buffer(30 * M_LAT))
            )
        )

    def sample(kind: str) -> Point:
        for _ in range(500):
            if kind == "water":
                c = river.interpolate(rng.uniform(0, 1), normalized=True)
                d = rng.uniform(60, 220)
                a = rng.uniform(0, 2 * math.pi)
                p = Point(c.x + d * math.cos(a) * m_lon(c.y), c.y + d * math.sin(a) * M_LAT)
            elif kind == "market" and markets:
                c = markets[int(rng.integers(len(markets)))]
                d, a = rng.uniform(80, 300), rng.uniform(0, 2 * math.pi)
                p = Point(c.x + d * math.cos(a) * m_lon(c.y), c.y + d * math.sin(a) * M_LAT)
            elif kind == "pilot":
                mx, my, Mx, My = pilot.bounds
                p = Point(rng.uniform(mx, Mx), rng.uniform(my, My))
                if not pilot.contains(p):
                    continue
            else:
                mx, my, Mx, My = GRID
                p = Point(rng.uniform(mx, Mx), rng.uniform(my, My))
            if ok(p):
                return p
        raise RuntimeError("no free location")

    kinds = ["pilot"] * 25 + ["water"] * 40 + ["market"] * 20 + ["any"] * 65
    devices = [f"demo-device-{i:02d}" for i in range(1, 51)]
    feats = []
    photo_seed = 1000
    for site_no, kind in enumerate(kinds, start=1):
        p = sample(kind)
        wtype = str(rng.choice(TYPES, p=TYPE_W))
        vol = str(rng.choice(VOLUMES, p=VOL_W))
        n = int(rng.choice([1, 2, 2, 3, 3, 4]))
        t = ANCHOR - timedelta(days=float(rng.uniform(1, 60)))
        devs = rng.choice(devices, size=n, replace=False)
        for k in range(n):
            jitter = rng.uniform(0, 12)
            a = rng.uniform(0, 2 * math.pi)
            lon = p.x + jitter * math.cos(a) * m_lon(p.y) + rng.uniform(-1e-6, 1e-6)
            lat = p.y + jitter * math.sin(a) * M_LAT + rng.uniform(-1e-6, 1e-6)
            photo_seed += 1
            feats.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [round(lon, 6) + 0.0000005, round(lat, 6) + 0.0000004],
                    },
                    "properties": {
                        "external_id": f"demo-{site_no:03d}-{k + 1}",
                        "waste_type": wtype,
                        "volume_class": vol,
                        "reported_at": t.isoformat(),
                        "device_id": str(devs[k]),
                        "accuracy": round(float(rng.uniform(4, 25)), 1),
                        "photo": f"demo-{photo_seed}.jpg",
                    },
                }
            )
            t += timedelta(hours=float(rng.uniform(2, 72)))
    (folder / "reports_demo.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False), encoding="utf-8"
    )
    jury = DATA / "jury"
    jury.mkdir(parents=True, exist_ok=True)
    pc = pilot.representative_point()
    rows = [["lat", "lon", "type", "volume", "date", "commentaire", "device_id"]]
    for i in range(8):
        q = sample("pilot")
        rows.append(
            [
                f"{q.y:.6f}",
                f"{q.x:.6f}",
                ["ménager", "plastique", "gravats", "mixte"][i % 4],
                "charrette",
                (ANCHOR - timedelta(hours=i * 5)).strftime("%d/%m/%Y %H:%M"),
                "",
                f"jury-{i % 3}",
            ]
        )
    rows.append(["", "", "plastique", "sac", "14/11/2026 10:00", "ligne sans coordonnées", "jury-x"])
    rows.append([f"{pc.y:.6f}", f"{pc.x:.6f}", "mixte", "sac", "31/02/2026", "date impossible", "jury-x"])
    with (jury / "exemple_import.csv").open("w", newline="", encoding="utf-8") as fh:
        csv.writer(fh, delimiter=";").writerows(rows)
    gj = []
    for i in range(4):
        q = sample("any")
        gj.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [round(q.x, 6), round(q.y, 6)]},
                "properties": {
                    "external_id": f"jury-geo-{i}",
                    "waste_type": "household",
                    "volume_class": "cart",
                    "reported_at": (ANCHOR - timedelta(days=i)).isoformat(),
                    "device_id": f"jury-geo-{i}",
                },
            }
        )
    q = sample("any")  # coordinates deliberately swapped
    gj.append(
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(q.y, 6), round(q.x, 6)]},
            "properties": {"external_id": "jury-geo-swapped", "waste_type": "plastic", "device_id": "jury-geo-9"},
        }
    )
    (jury / "exemple_import.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": gj}, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(
        f"{len(qf)} quartiers, {len(world.buildings)} bâtiments synthétiques, {len(kinds)} dépotoirs, "
        f"{len(feats)} signalements de démo"
    )


if __name__ == "__main__":
    main()
