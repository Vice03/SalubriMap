# SPDX-License-Identifier: AGPL-3.0-or-later
"""Download Google Open Buildings v3 tiles covering the work area and keep confidence >= 0.7 inside the bbox.

Run ONCE with Internet before the final; commit data/open_buildings/ouaga_buildings.csv.gz (CC-BY-4.0 / ODbL).
    python scripts/prepare_open_buildings.py [--min-confidence 0.7]
"""

import argparse
import csv
import gzip
import json
import sys

import httpx

from _common import DATA

# index des tuiles v3 (l'ancienne adresse sites.research.google/open-buildings/tiles.geojson répond 404)
TILES = "https://openbuildings-public-dot-gweb-research.uw.r.appspot.com/public/tiles.geojson"
csv.field_size_limit(sys.maxsize)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-confidence", type=float, default=0.7)
    a = ap.parse_args()
    bbox = json.loads((DATA / "osm" / "bbox.geojson").read_text())["features"][0]["geometry"]["coordinates"][0]
    x0, y0 = min(p[0] for p in bbox), min(p[1] for p in bbox)
    x1, y1 = max(p[0] for p in bbox), max(p[1] for p in bbox)
    from shapely.geometry import box, shape

    area = box(x0, y0, x1, y1)
    with httpx.Client(timeout=600, follow_redirects=True) as c:
        tiles = [f for f in c.get(TILES).json()["features"] if shape(f["geometry"]).intersects(area)]
        print(f"{len(tiles)} tuile(s) à télécharger")
        out = DATA / "open_buildings" / "ouaga_buildings.csv.gz"
        out.parent.mkdir(parents=True, exist_ok=True)
        n = 0
        with gzip.open(out, "wt", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["latitude", "longitude", "area_in_meters", "confidence", "geometry"])
            for t in tiles:
                url = t["properties"]["tile_url"]
                print("  ", url, f"({t['properties'].get('size_mb', '?')} Mo)")
                tmp = out.parent / "tuile.csv.gz.part"  # lu en flux : une tuile fait plus d'un gigaoctet
                with c.stream("GET", url) as r, tmp.open("wb") as fo:
                    r.raise_for_status()
                    for chunk in r.iter_bytes(1 << 20):
                        fo.write(chunk)
                with gzip.open(tmp, "rt", encoding="utf-8", newline="") as fi:
                    rows = list(_rows(fi, x0, y0, x1, y1, a.min_confidence))
                tmp.unlink()
                for row in rows:
                    w.writerow(row)
                    n += 1
    print(f"{n} bâtiments écrits dans {out}")


def _rows(fi, x0: float, y0: float, x1: float, y1: float, min_conf: float):  # type: ignore[no-untyped-def]
    for row in csv.DictReader(fi):
        lat, lon, conf = float(row["latitude"]), float(row["longitude"]), float(row["confidence"])
        if conf >= min_conf and x0 <= lon <= x1 and y0 <= lat <= y1:
            yield [lat, lon, row["area_in_meters"], conf, row["geometry"]]


if __name__ == "__main__":
    main()
