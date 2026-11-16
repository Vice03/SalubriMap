# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate the rehearsal trap set from the loaded database (works with the synthetic city AND real data).

Writes data/rehearsal/traps/<carte>/traps.geojson (+ photos referenced by name, rebuilt deterministically at
import time) and traps_expected.json, where <carte> names the loaded base map (services/dataset.py): a trap set
is only valid for the map it was generated on. rehearse.py picks the folder that matches the running API. Needs SALUBRI_DATABASE_URL (the seed must have run).

    python scripts/gen_traps.py
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text

from _common import DATA
from salubri_api.config import get_settings
from salubri_api.db import get_sessionmaker
from salubri_api.services.dataset import dataset_key

T0 = datetime(2026, 11, 16, 8, 0, tzinfo=UTC)


def main() -> None:
    feats: list[dict[str, Any]] = []
    expected: dict[str, Any] = {}
    seq = {"n": 0}
    photo_seed = {"n": 50_000}

    def photo(variant: str = "") -> str:
        photo_seed["n"] += 1
        return f"demo-{photo_seed['n']}{('-' + variant) if variant else ''}.jpg"

    def add(lon: float, lat: float, exp_status: list[str], rules: list[str], family: str, **props: Any) -> str:
        seq["n"] += 1
        eid = f"trap-{seq['n']:03d}-{family}"
        p = {
            "external_id": eid,
            "waste_type": "household",
            "volume_class": "cart",
            "accuracy": 8.0,
            "device_id": f"trap-dev-{seq['n']:03d}",
            "reported_at": (T0 + timedelta(minutes=seq["n"] * 7)).isoformat(),
            "photo": photo(),
        }
        p.update(props)
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": p})
        expected[eid] = {"family": family, "status": exp_status, "rules": rules}
        return eid

    with get_sessionmaker()() as s:
        cid = s.execute(text("SELECT id FROM communes WHERE slug = :s"), {"s": get_settings().commune}).scalar_one()
        out = DATA / "rehearsal" / "traps" / dataset_key(s, cid)

        def free_points(n: int, seed: float, min_gap_m: float = 80) -> list[tuple[float, float]]:
            rows = s.execute(
                text("""
                WITH q AS (SELECT geom FROM quartiers WHERE commune_id = :c ORDER BY name LIMIT 6),
                     pts AS (SELECT (ST_Dump(ST_GeneratePoints(ST_Union(geom), 3000, :seed))).geom AS g FROM q)
                SELECT ST_X(g) AS lon, ST_Y(g) AS lat FROM pts
                WHERE NOT EXISTS (SELECT 1 FROM buildings b WHERE b.commune_id = :c AND ST_DWithin(b.geom, pts.g, 0.0002)
                                  AND ST_DWithin(b.geom::geography, pts.g::geography, 6))
                  AND NOT EXISTS (SELECT 1 FROM water w WHERE w.commune_id = :c AND ST_DWithin(w.geom, pts.g, 0.002)
                                  AND ST_DWithin(w.geom::geography, pts.g::geography, 40))
                  AND NOT EXISTS (SELECT 1 FROM reports r WHERE r.commune_id = :c AND ST_DWithin(r.geom, pts.g, 0.002)
                                  AND ST_DWithin(r.geom::geography, pts.g::geography, 120))
                  AND NOT EXISTS (SELECT 1 FROM pois p WHERE p.commune_id = :c AND p.kind IN ('hospital','clinic','doctors')
                                  AND ST_DWithin(p.geom::geography, pts.g::geography, 350))"""),
                {"c": cid, "seed": int(seed)},
            ).all()
            out: list[tuple[float, float]] = []
            for r in rows:
                if all(abs(r.lon - o[0]) * 108_000 > min_gap_m or abs(r.lat - o[1]) * 111_000 > min_gap_m for o in out):
                    out.append((round(r.lon, 6) + 3e-7, round(r.lat, 6) + 2e-7))
                if len(out) >= n:
                    break
            if len(out) < n:
                raise SystemExit("Pas assez d'emplacements libres : lancer le seed d'abord")
            return out

        pts = iter(free_points(60, 11))
        m = 1 / 111_000

        # Controls
        for _ in range(5):
            lon, lat = next(pts)
            add(lon, lat, ["probable"], [], "control")
        # R1: same device, 10-25 m, 5 h later
        for k in range(3):
            lon, lat = next(pts)
            dev = f"trap-r1-{k}"
            add(lon, lat, ["probable"], [], "r1-first", device_id=dev)
            add(
                lon + 15 * m,
                lat,
                ["to_review"],
                ["R1"],
                "r1-dup",
                device_id=dev,
                reported_at=(T0 + timedelta(hours=5 + k)).isoformat(),
            )
        # R2: identical photo, then re-compressed photo
        lon, lat = next(pts)
        same = photo()
        add(lon, lat, ["probable"], [], "r2-source", photo=same)
        lon, lat = next(pts)
        add(lon, lat, ["rejected"], ["R2"], "r2-identical", photo=same)
        lon, lat = next(pts)
        src = photo()
        add(lon, lat, ["probable"], [], "r2-source", photo=src)
        lon, lat = next(pts)
        add(lon, lat, ["to_review", "rejected"], ["R2"], "r2-recompressed", photo=src.replace(".jpg", "-q30.jpg"))
        # R3 / R4: EXIF
        lon, lat = next(pts)
        add(
            lon,
            lat,
            ["probable", "to_review"],
            ["R3"],
            "r3-exif-gps",
            photo=photo(f"exifgps_{lat + 0.05:.5f}_{lon:.5f}"),
        )
        lon, lat = next(pts)
        add(lon, lat, ["probable"], ["R4"], "r4-exif-old", photo=photo("exifold"))
        # R5: outside the commune
        for lon, lat, name in ((-4.2967, 11.1771, "bobo"), (-2.3627, 12.2526, "koudougou"), (1.0, 4.0, "golfe")):
            add(lon + 1e-6, lat + 1e-6, ["rejected"], ["R5"], f"r5-{name}")
        # R6: inside buildings
        blds = s.execute(
            text("""SELECT ST_X(ST_Centroid(geom)) AS lon, ST_Y(ST_Centroid(geom)) AS lat, area_m2 FROM buildings
                                 WHERE commune_id = :c AND confidence >= 0.7 AND area_m2 BETWEEN 60 AND 2000
                                 ORDER BY area_m2 DESC LIMIT 400"""),
            {"c": cid},
        ).all()
        for b in (blds[0], blds[len(blds) // 2], blds[-1]):
            add(round(b.lon, 7) + 1e-7, round(b.lat, 7) + 1e-7, ["to_review", "rejected"], ["R6"], "r6-building")
        # R7: reservoir (reject) and river
        res = s.execute(
            text("""SELECT ST_X(ST_PointOnSurface(geom)) AS lon, ST_Y(ST_PointOnSurface(geom)) AS lat
                                FROM water WHERE commune_id = :c AND kind = 'water' AND area_m2 > 10000
                                ORDER BY area_m2 DESC LIMIT 2"""),
            {"c": cid},
        ).all()
        for r in res:
            add(round(r.lon, 7) + 1e-7, round(r.lat, 7) + 1e-7, ["rejected"], ["R7"], "r7-reservoir")
        riv = s.execute(
            text("""SELECT ST_X(ST_LineInterpolatePoint(geom, 0.4)) AS lon, ST_Y(ST_LineInterpolatePoint(geom, 0.4)) AS lat
                                FROM water WHERE commune_id = :c AND kind = 'waterway' AND GeometryType(geom) = 'LINESTRING'
                                ORDER BY ST_Length(geom::geography) DESC LIMIT 1"""),
            {"c": cid},
        ).first()
        if riv:
            add(round(riv.lon, 7) + 1e-7, round(riv.lat, 7) + 1e-7, ["to_review", "rejected"], ["R7"], "r7-river")
        # R8: fake GPS
        add(0.0, 0.0, ["rejected"], ["R8"], "r8-zero")
        lon, lat = next(pts)
        add(round(lon, 3), round(lat, 3), ["probable", "to_review"], ["R8"], "r8-rounded")
        lon, lat = next(pts)
        add(lon, lat, ["probable"], ["R8"], "r8-accuracy", accuracy=900)
        demo = s.execute(
            text("""SELECT ST_X(geom) AS lon, ST_Y(geom) AS lat, waste_type FROM reports
                                 WHERE commune_id = :c AND status IN ('verified','probable') AND device_id NOT LIKE 'trap%'
                                 ORDER BY external_id LIMIT 1"""),
            {"c": cid},
        ).first()
        if demo:
            other = "rubble" if demo.waste_type != "rubble" else "plastic"
            add(demo.lon, demo.lat, ["to_review", "rejected"], ["R8"], "r8-copied-point", waste_type=other)
        # R9: same device jumps across the city in 3 minutes
        a = next(pts)
        far = s.execute(
            text("""SELECT ST_X(c) AS lon, ST_Y(c) AS lat FROM (SELECT ST_Centroid(geom) AS c FROM quartiers
                                WHERE commune_id = :c ORDER BY name DESC LIMIT 1) z"""),
            {"c": cid},
        ).first()
        add(
            a[0],
            a[1],
            ["probable"],
            [],
            "r9-first",
            device_id="trap-r9",
            reported_at=(T0 + timedelta(hours=10)).isoformat(),
        )
        add(
            round(far.lon, 6) + 3e-7,
            round(far.lat, 6) + 2e-7,
            ["to_review", "probable", "rejected"],
            ["R9"],
            "r9-jump",
            device_id="trap-r9",
            reported_at=(T0 + timedelta(hours=10, minutes=3)).isoformat(),
        )
        # R10: 12 reports in 20 minutes from one device (40 m apart: no R1, no R9)
        lon0, lat0 = next(pts)
        for k in range(12):
            exp = (["probable"], []) if k < 10 else (["probable", "to_review"], ["R10"])
            add(
                lon0 + (k % 4) * 45 * m,
                lat0 + (k // 4) * 45 * m,
                exp[0],
                exp[1],
                "r10-burst",
                device_id="trap-spam",
                waste_type=["household", "plastic", "mixed"][k % 3],
                reported_at=(T0 + timedelta(hours=12, minutes=k * 1.6)).isoformat(),
            )
        for k in range(5):
            lon, lat = next(pts)
            add(
                lon,
                lat,
                ["probable"] if k < 4 else ["probable", "to_review"],
                [] if k < 4 else ["R10"],
                "r10-comment",
                comment="Gros tas d'ordures ici",
                reported_at=(T0 + timedelta(hours=14, minutes=k * 9)).isoformat(),
            )
        # R11: black screen, tiny image
        lon, lat = next(pts)
        add(lon, lat, ["probable"], ["R11"], "r11-dark", photo=photo("dark"))
        lon, lat = next(pts)
        add(lon, lat, ["probable"], ["R11"], "r11-small", photo=photo("small"))
        # R12: "truck" volume with a 20 KB photo, medical waste far from any health centre
        lon, lat = next(pts)
        add(lon, lat, ["probable"], ["R12"], "r12-truck-light", volume_class="truck", photo=photo("tiny"))
        lon, lat = next(pts)
        add(lon, lat, ["probable"], ["R12"], "r12-medical", waste_type="medical")
        # Combined: building + reused photo
        add(
            round(blds[5].lon, 7) + 1e-7,
            round(blds[5].lat, 7) + 1e-7,
            ["rejected"],
            ["R2", "R6"],
            "combined",
            photo=same,
        )

    out.mkdir(parents=True, exist_ok=True)
    (out / "traps.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (out / "traps_expected.json").write_text(json.dumps(expected, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(feats)} signalements piégés écrits dans {out}")


if __name__ == "__main__":
    main()
