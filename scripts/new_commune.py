# SPDX-License-Identifier: AGPL-3.0-or-later
"""Create data/communes/<slug>/ with templates (see docs/NOUVELLE_COMMUNE.md)."""

import argparse
import json
import shutil

from _common import DATA


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--name", required=True)
    ap.add_argument("--bbox", required=True, help="minLon,minLat,maxLon,maxLat")
    ap.add_argument("--depot", required=True, help="lon,lat du garage / centre d'enfouissement")
    a = ap.parse_args()
    folder = DATA / "communes" / a.slug
    if folder.exists():
        raise SystemExit(f"{folder} existe déjà")
    folder.mkdir(parents=True)
    x0, y0, x1, y1 = (float(v) for v in a.bbox.split(","))
    depot = [float(v) for v in a.depot.split(",")]
    (folder / "commune.json").write_text(
        json.dumps(
            {
                "slug": a.slug,
                "name": a.name,
                "bbox": [x0, y0, x1, y1],
                "depot": depot,
                "osm_extract": f"{a.slug}.osm.pbf",
                "buildings": f"{a.slug}_buildings.csv.gz",
                "scenarios": [{"name": "Base", "baseline": True, "quartiers": None}],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = (x1 - x0) / 4, (y1 - y0) / 4
    (folder / "quartiers.geojson").write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"name": "Secteur 1 (à remplacer)", "population": 20000},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [cx - dx, cy - dy],
                                    [cx + dx, cy - dy],
                                    [cx + dx, cy + dy],
                                    [cx - dx, cy + dy],
                                    [cx - dx, cy - dy],
                                ]
                            ],
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    src = DATA / "communes" / "ouagadougou"
    shutil.copy(src / "params_default.json", folder / "params_default.json")
    shutil.copy(src / "vehicles.csv", folder / "vehicles.csv")
    print(f"Gabarits créés dans {folder} : remplir quartiers.geojson, params_default.json et vehicles.csv")


if __name__ == "__main__":
    main()
