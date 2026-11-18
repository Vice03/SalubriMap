# SPDX-License-Identifier: AGPL-3.0-or-later
"""Verified reports -> dump sites (DBSCAN, 30 m). Existing sites keep their id, cleaning history and osm_id."""

import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
from shapely.geometry import MultiPoint, Point
from sklearn.cluster import DBSCAN
from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api.models import DumpSite, Report, utcnow
from salubri_api.services.geo import EARTH_R_M, haversine_m, metres_to_deg_lat, shape, to_wkb

VOLUME_M3 = {"bag": 0.05, "wheelbarrow": 0.1, "cart": 0.6, "truck": 6.0, "more": 12.0}
RECURRING_DAYS = 15


@dataclass
class Cluster:
    report_ids: list[uuid.UUID]
    lat: float
    lon: float
    points: list[tuple[float, float]]
    volume_m3: float
    dominant_type: str
    first_at: datetime
    last_at: datetime
    mean_score: float


def cluster_reports(
    rows: list[tuple[uuid.UUID, float, float, str, str, datetime, int]], eps_m: float = 30.0
) -> list[Cluster]:
    """rows: (id, lat, lon, waste_type, volume_class, reported_at, score). Pure function."""
    if not rows:
        return []
    coords = np.radians(np.array([[r[1], r[2]] for r in rows]))
    labels = DBSCAN(eps=eps_m / EARTH_R_M, min_samples=1, metric="haversine").fit(coords).labels_
    out: list[Cluster] = []
    for lab in sorted(set(labels)):
        members = [rows[i] for i in np.where(labels == lab)[0]]
        lats = [m[1] for m in members]
        lons = [m[2] for m in members]
        # Several reports of one dump describe the same heap: take the largest estimate, not the sum.
        vol = max(VOLUME_M3[m[4]] for m in members)
        out.append(
            Cluster(
                report_ids=[m[0] for m in members],
                lat=float(np.mean(lats)),
                lon=float(np.mean(lons)),
                points=list(zip(lons, lats, strict=True)),
                volume_m3=vol,
                dominant_type=Counter(m[3] for m in members).most_common(1)[0][0],
                first_at=min(m[5] for m in members),
                last_at=max(m[5] for m in members),
                mean_score=float(np.mean([m[6] for m in members])),
            )
        )
    return out


def priority(volume_m3: float, near_water: bool, first_at: datetime, now: datetime, near_drain: bool = False) -> float:
    """Volume × eau × ancienneté. Un dépotoir dans ou au bord d'un caniveau le bouche : inondations en saison des
    pluies, d'où × 2 (au lieu de × 1,5 près d'un autre cours d'eau)."""
    age_days = max((now - first_at).total_seconds() / 86400, 0)
    w = 2.0 if near_drain else 1.5 if near_water else 1.0
    return round(volume_m3 * w * (1 + age_days / 30), 3)


DRAIN_KINDS = ("drain", "ditch")  # OSM waterway=drain (caniveau maçonné), ditch (fossé)
DRAIN_DIST_M = 15


def consolidate(s: Session, commune_id: uuid.UUID, eps_m: float = 30.0) -> dict[str, int]:
    rows = s.execute(
        text("""SELECT id, ST_Y(geom), ST_X(geom), waste_type, volume_class, reported_at, score
                             FROM reports WHERE commune_id = :c AND status = 'verified'"""),
        {"c": commune_id},
    ).all()
    from salubri_api.config import get_settings

    if get_settings().seasons_enabled:  # module « Saisons » : une route impraticable n'est pas un dépotoir
        from salubri_api.modules.seasons.models import RoadReport

        roads = {r for (r,) in s.query(RoadReport.report_id).all()}
        rows = [r for r in rows if r[0] not in roads]
    clusters = cluster_reports([tuple(r) for r in rows], eps_m)  # type: ignore[misc]
    existing = s.query(DumpSite).filter(DumpSite.commune_id == commune_id).all()
    ex_pts = [(d, shape(d.geom)) for d in existing]
    used: set[uuid.UUID] = set()
    now = utcnow()
    created = updated = 0
    for c in clusters:
        match = None
        for d, p in ex_pts:
            if d.id not in used and haversine_m(c.lat, c.lon, p.y, p.x) <= eps_m:
                match = d
                break
        near_water = bool(
            s.execute(
                text("""SELECT EXISTS (SELECT 1 FROM water WHERE commune_id = :c
            AND ST_DWithin(geom, ST_SetSRID(ST_MakePoint(:lon,:lat),4326), 0.002)
            AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography, 50))"""),
                {"c": commune_id, "lon": c.lon, "lat": c.lat},
            ).scalar()
        )
        near_drain = bool(
            s.execute(
                text("""SELECT EXISTS (SELECT 1 FROM water WHERE commune_id = :c AND subkind IN ('drain', 'ditch')
            AND ST_DWithin(geom, ST_SetSRID(ST_MakePoint(:lon,:lat),4326), 0.001)
            AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography, :d))"""),
                {"c": commune_id, "lon": c.lon, "lat": c.lat, "d": DRAIN_DIST_M},
            ).scalar()
        )
        hull = MultiPoint(c.points).convex_hull.buffer(metres_to_deg_lat(6))
        if match is None:
            match = DumpSite(
                commune_id=commune_id,
                status="active",
                first_reported_at=c.first_at,
                last_reported_at=c.last_at,
                dominant_type=c.dominant_type,
                geom=to_wkb(Point(c.lon, c.lat)),
            )
            s.add(match)
            created += 1
        else:
            updated += 1
            if match.status == "cleaned" and match.cleaned_at and c.last_at > match.cleaned_at:
                recur = c.last_at - match.cleaned_at <= timedelta(days=RECURRING_DAYS)
                match.status = "recurring" if recur else "active"
        match.geom = to_wkb(Point(c.lon, c.lat))
        match.hull = to_wkb(hull)
        match.dominant_type = c.dominant_type
        match.volume_est_m3 = c.volume_m3
        match.n_reports = len(c.report_ids)
        match.first_reported_at = min(match.first_reported_at or c.first_at, c.first_at)
        match.last_reported_at = c.last_at
        match.near_water = near_water or near_drain
        match.near_drain = near_drain
        match.mean_score = round(c.mean_score, 1)
        match.priority = priority(c.volume_m3, near_water or near_drain, c.first_at, now, near_drain)
        s.flush()
        used.add(match.id)
        s.query(Report).filter(Report.id.in_(c.report_ids)).update(
            {Report.dump_site_id: match.id}, synchronize_session=False
        )
    removed = 0
    for d, _ in ex_pts:
        if d.id not in used and d.status in ("active", "recurring"):
            s.query(Report).filter(Report.dump_site_id == d.id, Report.status != "cleaned").update(
                {Report.dump_site_id: None}, synchronize_session=False
            )
            s.delete(d)
            removed += 1
    s.flush()
    from salubri_api.services.laabal import auto_transmit

    auto_transmit(s, commune_id)  # un dépotoir qui revient après nettoyage part seul à la brigade Laabal
    return {"clusters": len(clusters), "created": created, "updated": updated, "removed": removed}


def mark_cleaned(s: Session, site: DumpSite) -> None:
    site.status = "cleaned"
    site.cleaned_at = utcnow()
    s.query(Report).filter(Report.dump_site_id == site.id, Report.status == "verified").update(
        {Report.status: "cleaned"}, synchronize_session=False
    )
