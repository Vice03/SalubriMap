# SPDX-License-Identifier: AGPL-3.0-or-later
"""Persist ilots of a quartier (used by the seed and by « nouveau quartier »)."""

from shapely.geometry import Point
from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api.models import Ilot, Quartier
from salubri_api.services.demand import build_ilots
from salubri_api.services.geo import shape, to_wkb


def rebuild_ilots(s: Session, q: Quartier, target_size: int = 30, seed: int = 42) -> int:
    s.query(Ilot).filter(Ilot.quartier_id == q.id).delete(synchronize_session=False)
    rows = s.execute(
        text("""SELECT ST_X(ST_Centroid(b.geom)), ST_Y(ST_Centroid(b.geom)), b.area_m2
                             FROM buildings b, quartiers q WHERE q.id = :q AND b.commune_id = q.commune_id
                               AND b.confidence >= 0.7 AND ST_Contains(q.geom, ST_Centroid(b.geom))"""),
        {"q": q.id},
    ).all()
    drafts = build_ilots(
        str(q.id),
        shape(q.geom),
        float(q.population),
        [tuple(r) for r in rows],  # type: ignore[misc]
        target_size,
        seed,
    )
    objs = [
        Ilot(
            quartier_id=q.id,
            geom=to_wkb(d.polygon),
            centroid=to_wkb(Point(d.lon, d.lat)),
            n_buildings=d.n_buildings,
            population=d.population,
        )
        for d in drafts
    ]
    s.add_all(objs)
    s.flush()
    s.execute(
        text("""UPDATE ilots i SET near_water = EXISTS (
                        SELECT 1 FROM water w WHERE w.commune_id = q.commune_id
                          AND ST_DWithin(w.geom, i.centroid, 0.002)
                          AND ST_DWithin(w.geom::geography, i.centroid::geography, 50))
                      FROM quartiers q WHERE q.id = i.quartier_id AND i.quartier_id = :q"""),
        {"q": q.id},
    )
    return len(objs)
