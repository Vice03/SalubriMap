# SPDX-License-Identifier: AGPL-3.0-or-later
"""Deterministic synthetic city used when the real OSM / Open Buildings extracts are not in data/ yet.

It is plausible, not real: a road grid, a river with three reservoirs, compounds between the roads, schools,
markets and health centres. Replace it by running scripts/prepare_osm_extract.sh and
scripts/prepare_open_buildings.py (see data/README.md).
"""

import io
import math
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from shapely.geometry import LineString, Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.strtree import STRtree

M_LAT = 1 / 111_320.0


def m_lon(lat: float) -> float:
    return 1 / (111_320.0 * math.cos(math.radians(lat)))


@dataclass
class World:
    roads: list[tuple[LineString, str, str | None, bool]]  # geom, highway, surface, truck_ok
    water: list[tuple[BaseGeometry, str, str, bool]]  # geom, kind, name, flood_prone
    pois: list[tuple[BaseGeometry, str, str]]  # geom, kind, name
    buildings: list[tuple[float, float, float, float]]  # minx, miny, maxx, maxy (lon/lat)


def _river(bbox: tuple[float, float, float, float]) -> LineString:
    x0, y0, x1, y1 = bbox
    xs = np.linspace(x0, x1, 40)
    ys = y0 + (y1 - y0) * (0.55 + 0.08 * np.sin(np.linspace(0, 3 * math.pi, 40)) + 0.12 * np.linspace(-1, 1, 40))
    return LineString(list(zip(xs, ys, strict=True)))


def build_world(
    bbox: tuple[float, float, float, float],
    quartiers: list[tuple[str, BaseGeometry, int]],
    seed: int = 7,
    people_per_building: float = 25.0,
) -> World:
    rng = np.random.default_rng(seed)
    x0, y0, x1, y1 = bbox
    lat0 = (y0 + y1) / 2
    dx, dy = 300 * m_lon(lat0), 300 * M_LAT
    roads: list[tuple[LineString, str, str | None, bool]] = []
    i = 0
    x = x0
    while x <= x1:
        hw = "primary" if i % 4 == 0 else "residential"
        roads.append((LineString([(x, y0), (x, y1)]), hw, "asphalt" if hw == "primary" else "unpaved", True))
        x += dx
        i += 1
    j = 0
    y = y0
    while y <= y1:
        hw = "primary" if j % 4 == 0 else "residential"
        roads.append((LineString([(x0, y), (x1, y)]), hw, "asphalt" if hw == "primary" else "unpaved", True))
        y += dy
        j += 1

    river = _river(bbox)
    water: list[tuple[BaseGeometry, str, str, bool]] = [(river, "waterway", "Marigot (synthétique)", True)]
    for k, frac in enumerate((0.35, 0.5, 0.65), start=1):
        c = river.interpolate(frac, normalized=True)
        rx, ry = 450 * m_lon(lat0), 220 * M_LAT
        ang = np.linspace(0, 2 * math.pi, 32)
        poly = Polygon([(c.x + rx * math.cos(a), c.y + ry * math.sin(a)) for a in ang])
        water.append((poly, "water", f"Barrage n°{k} (synthétique)", False))
    water_zone = unary_union([river.buffer(25 * M_LAT)] + [w[0].buffer(30 * M_LAT) for w in water[1:]])

    pois: list[tuple[BaseGeometry, str, str]] = []
    road_tree = STRtree([r[0] for r in roads])
    road_lines = [r[0] for r in roads]

    def free_point(qgeom: BaseGeometry) -> Point:
        minx, miny, maxx, maxy = qgeom.bounds
        for _ in range(200):
            p = Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy))
            if qgeom.contains(p) and not water_zone.contains(p):
                return p
        return qgeom.representative_point()

    buildings: list[tuple[float, float, float, float]] = []
    for qi, (name, qgeom, pop) in enumerate(quartiers):
        if qi % 3 == 0:
            pois.append((free_point(qgeom), "hospital" if qi % 6 == 0 else "clinic", f"Centre de santé {name}"))
        pois.append((free_point(qgeom), "school", f"École {name}"))
        if qi % 3 == 1:
            m = free_point(qgeom)
            pois.append((m.buffer(60 * M_LAT), "marketplace", f"Marché {name}"))
        n = max(1, int(pop / people_per_building))
        minx, miny, maxx, maxy = qgeom.bounds
        cand = np.column_stack([rng.uniform(minx, maxx, n * 3), rng.uniform(miny, maxy, n * 3)])
        placed = 0
        for cx, cy in cand:
            if placed >= n:
                break
            p = Point(cx, cy)
            if not qgeom.contains(p) or water_zone.contains(p):
                continue
            near = road_tree.query(p.buffer(14 * M_LAT))
            if any(road_lines[k].distance(p) < 14 * M_LAT for k in near):
                continue
            side = rng.uniform(9, 20)
            hx, hy = side / 2 * m_lon(cy), side / 2 * M_LAT
            buildings.append((cx - hx, cy - hy, cx + hx, cy + hy))
            placed += 1
    return World(roads, water, pois, buildings)


def building_polygon(b: tuple[float, float, float, float]) -> Polygon:
    return box(*b)


def synthetic_photo(seed: int, size: tuple[int, int] = (640, 480), dark: bool = False) -> bytes:
    """A unique, dump-like JPEG (coloured heaps on soil) so that pHash differs between reports."""
    rng = np.random.default_rng(seed)
    w, h = size
    soil = tuple(int(v) for v in rng.integers([150, 100, 60], [200, 140, 90]))
    img = Image.new("RGB", size, (0, 0, 0) if dark else soil)
    if not dark:
        d = ImageDraw.Draw(img)
        for _ in range(int(rng.integers(25, 60))):
            cx, cy = rng.integers(0, w), rng.integers(h // 4, h)
            r = int(rng.integers(8, 70))
            col = tuple(int(v) for v in rng.integers(0, 255, 3))
            if rng.random() < 0.5:
                d.ellipse([cx - r, cy - r // 2, cx + r, cy + r // 2], fill=col)
            else:
                d.rectangle([cx - r, cy - r // 3, cx + r // 2, cy + r // 2], fill=col)
        noise = rng.integers(0, 40, (h, w, 3), dtype=np.uint8)
        img = Image.fromarray(np.clip(np.asarray(img, dtype=np.int16) + noise - 20, 0, 255).astype(np.uint8))
        img = img.filter(ImageFilter.GaussianBlur(0.6))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return buf.getvalue()


def _jpeg(img: Image.Image, quality: int = 88, exif: Image.Exif | None = None) -> bytes:
    buf = io.BytesIO()
    if exif is not None:
        img.save(buf, "JPEG", quality=quality, exif=exif)
    else:
        img.save(buf, "JPEG", quality=quality)
    return buf.getvalue()


def _dms(v: float) -> tuple[float, float, float]:
    v = abs(v)
    d = int(v)
    m = int((v - d) * 60)
    return (float(d), float(m), round((v - d - m / 60) * 3600, 4))


def photo_for_name(name: str) -> bytes | None:
    """Deterministic test photos named demo-<seed>[-variant].jpg, used by the demo data and the trap set.

    Variants: dark (black screen), small (120x90), q30 (same picture re-compressed: same pHash, other SHA),
    tiny (heavily compressed, < 50 KB), exifgps_<lat>_<lon> (EXIF GPS), exifold (EXIF date in 2024).
    """
    if not name.startswith("demo-"):
        return None
    stem = name.rsplit(".", 1)[0]
    parts = stem.split("-")
    try:
        seed = int(parts[1])
    except (IndexError, ValueError):
        return None
    variant = "-".join(parts[2:])
    if variant == "dark":
        return synthetic_photo(seed, dark=True)
    base = Image.open(io.BytesIO(synthetic_photo(seed)))
    if variant == "small":
        return _jpeg(base.resize((120, 90)))
    if variant == "q30":
        return _jpeg(base, quality=30)
    if variant == "tiny":
        return _jpeg(base.resize((320, 240)), quality=8)
    if variant.startswith("exifgps_"):
        _, lat_s, lon_s = variant.split("_")
        lat, lon = float(lat_s), float(lon_s)
        ex = Image.Exif()
        ex[0x8825] = {1: "N" if lat >= 0 else "S", 2: _dms(lat), 3: "E" if lon >= 0 else "W", 4: _dms(lon)}
        return _jpeg(base, exif=ex)
    if variant == "exifold":
        ex = Image.Exif()
        ex[0x0132] = "2024:01:05 10:00:00"
        ex[0x8769] = {36867: "2024:01:05 10:00:00"}
        return _jpeg(base, exif=ex)
    return synthetic_photo(seed)
