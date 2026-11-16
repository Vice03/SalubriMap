# SPDX-License-Identifier: AGPL-3.0-or-later
"""Load Open Buildings v3 polygons (CSV or CSV.GZ with a WKT `geometry` column) in batches."""

import csv
import gzip
import io
import logging
import uuid
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("salubri.seed")
BATCH = 5000


def load_buildings(s: Session, commune_id: uuid.UUID, path: Path, min_confidence: float = 0.7) -> int:
    opener = gzip.open if path.suffix == ".gz" else open
    n = 0
    batch: list[dict[str, object]] = []
    with opener(path, "rt", encoding="utf-8") as fh:  # type: ignore[operator]
        for row in csv.DictReader(fh if isinstance(fh, io.TextIOBase) else fh):
            conf = float(row.get("confidence") or 0)
            if conf < min_confidence or not row.get("geometry"):
                continue
            batch.append(
                {"c": commune_id, "wkt": row["geometry"], "area": float(row.get("area_in_meters") or 0), "conf": conf}
            )
            if len(batch) >= BATCH:
                n += _flush(s, batch)
                batch = []
    n += _flush(s, batch)
    log.info("Open Buildings : %s bâtiments", n)
    return n


def _flush(s: Session, rows: list[dict[str, object]]) -> int:
    if not rows:
        return 0
    s.execute(
        text("""INSERT INTO buildings (id, commune_id, geom, area_m2, confidence, source)
                      VALUES (gen_random_uuid(), :c, ST_GeometryN(ST_Multi(ST_GeomFromText(:wkt, 4326)), 1),
                              :area, :conf, 'open_buildings')"""),
        rows,
    )
    return len(rows)
