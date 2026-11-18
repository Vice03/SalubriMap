# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validation engine: builds a ReportContext with PostGIS queries, applies R1-R12, sets score and status.

Only reports *earlier* than the one being evaluated count as "previous" evidence (duplicates, reused
photos, copied coordinates), so re-validating a report gives the same answer as when it arrived.
"""

import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api.models import Device, Photo, Report, utcnow
from salubri_api.services.params import ValidationThresholds
from salubri_api.services.validation.photo import PhotoInfo, hamming
from salubri_api.services.validation.rules import Neighbor, ReportContext, RuleHit, all_rules

PT = "ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)"
DEG_PREFILTER = 0.01  # ~1 km, lets the GiST index on geom do the first cut


@dataclass
class Evaluation:
    score: int
    status: str
    hits: list[RuleHit] = field(default_factory=list)
    duplicate_of: str | None = None

    @property
    def hits_json(self) -> list[dict[str, Any]]:
        return [h.as_dict() for h in self.hits]


def evaluate(ctx: ReportContext, th: ValidationThresholds) -> Evaluation:
    hits: list[RuleHit] = []
    for rule in all_rules():
        hit = rule.apply(ctx, th)
        if hit is not None:
            hits.append(hit)
    rejected = any(h.reject for h in hits)
    score = 0 if rejected else max(0, 100 + sum(h.delta for h in hits))
    if rejected or score < th.review_min:
        status = "rejected"
    elif score >= th.probable_min:
        status = "probable"
    else:
        status = "to_review"
    dup = next((h.duplicate_of for h in hits if h.duplicate_of), None)
    return Evaluation(score=score, status=status, hits=hits, duplicate_of=dup)


def photo_info_from_row(p: Photo) -> PhotoInfo:
    return PhotoInfo(
        sha256=p.sha256,
        phash=p.phash,
        width=p.width,
        height=p.height,
        bytes=p.bytes,
        exif_lat=p.exif_lat,
        exif_lon=p.exif_lon,
        exif_taken_at=p.exif_taken_at,
        luminance_var=p.luminance_var,
    )


def build_context(
    s: Session, report: Report, lat: float, lon: float, photo: PhotoInfo | None, th: ValidationThresholds
) -> ReportContext:
    rid = report.id
    t = report.reported_at
    base = {"lat": lat, "lon": lon, "cid": report.commune_id, "rid": rid, "t": t, "pf": DEG_PREFILTER}
    ctx = ReportContext(
        lat=lat,
        lon=lon,
        accuracy_m=report.gps_accuracy_m,
        waste_type=report.waste_type,
        volume_class=report.volume_class,
        comment=report.comment,
        reported_at=t,
        device_id=report.device_id,
        photo=photo,
    )

    rows = s.execute(
        text(f"""
        SELECT id, ST_Distance(geom::geography, {PT}::geography) AS d, waste_type, reported_at, device_id, status
        FROM reports
        WHERE commune_id = :cid AND id <> :rid AND reported_at <= :t
          AND ST_DWithin(geom, {PT}, :pf)
          AND ST_DWithin(geom::geography, {PT}::geography, :r)
        ORDER BY reported_at"""),
        {**base, "r": max(th.duplicate_radius_m, th.same_point_m)},
    ).all()
    ctx.neighbors = [Neighbor(str(r.id), float(r.d), r.waste_type, r.reported_at, r.device_id, r.status) for r in rows]
    for n in ctx.neighbors:
        if n.distance_m <= th.same_point_m and (ctx.device_id is None or n.device_id != ctx.device_id):
            ctx.same_point_other_device = n.report_id
            break

    if photo is not None:
        row = s.execute(
            text("""
            SELECT p.report_id FROM photos p JOIN reports r ON r.id = p.report_id
            WHERE p.sha256 = :sha AND p.report_id <> :rid AND r.reported_at <= :t
            ORDER BY r.reported_at LIMIT 1"""),
            {"sha": photo.sha256, "rid": rid, "t": t},
        ).first()
        if row:
            ctx.photo_same_sha = str(row.report_id)
        else:
            b = photo.bands
            cands = s.execute(
                text("""
                SELECT p.report_id, p.phash FROM photos p JOIN reports r ON r.id = p.report_id
                WHERE p.report_id <> :rid AND r.reported_at <= :t
                  AND (p.phash_b0 = :b0 OR p.phash_b1 = :b1 OR p.phash_b2 = :b2 OR p.phash_b3 = :b3)"""),
                {"rid": rid, "t": t, "b0": b[0], "b1": b[1], "b2": b[2], "b3": b[3]},
            ).all()
            best = min(
                ((str(c.report_id), hamming(c.phash, photo.phash)) for c in cands), key=lambda x: x[1], default=None
            )
            if best is not None and best[1] <= th.phash_max_hamming:
                ctx.photo_similar = best

    n_quartiers = s.execute(text("SELECT count(*) FROM quartiers WHERE commune_id = :cid"), base).scalar_one()
    if n_quartiers:
        ctx.in_zone = bool(
            s.execute(
                text(f"""
            SELECT EXISTS (SELECT 1 FROM quartiers WHERE commune_id = :cid
              AND ST_DWithin(geom::geography, {PT}::geography, :buf))"""),
                {**base, "buf": th.zone_buffer_m},
            ).scalar()
        )

    ctx.building_area_m2 = s.execute(
        text(f"""
        SELECT area_m2 FROM buildings WHERE commune_id = :cid AND confidence >= :conf
          AND ST_Contains(geom, {PT}) ORDER BY area_m2 DESC LIMIT 1"""),
        {**base, "conf": th.building_min_confidence},
    ).scalar()

    ctx.in_water_area_m2 = s.execute(
        text(f"""
        SELECT area_m2 FROM water WHERE commune_id = :cid AND kind IN ('water','wetland')
          AND ST_Contains(geom, {PT}) ORDER BY area_m2 DESC LIMIT 1"""),
        base,
    ).scalar()
    ctx.near_waterway = bool(
        s.execute(
            text(f"""
        SELECT EXISTS (SELECT 1 FROM water WHERE commune_id = :cid AND kind = 'waterway'
          AND coalesce(subkind, '') NOT IN ('drain', 'ditch')  -- un dépôt dans un caniveau est un vrai cas
          AND ST_DWithin(geom, {PT}, :pf)
          AND ST_DWithin(geom::geography, {PT}::geography, :buf))"""),
            {**base, "buf": th.waterway_buffer_m},
        ).scalar()
    )

    if report.waste_type == "medical":
        n_med = s.execute(
            text("""SELECT count(*) FROM pois WHERE commune_id = :cid
                                  AND kind IN ('hospital','clinic','doctors')"""),
            base,
        ).scalar_one()
        if n_med:
            ctx.near_medical_poi = bool(
                s.execute(
                    text(f"""
                SELECT EXISTS (SELECT 1 FROM pois WHERE commune_id = :cid AND kind IN ('hospital','clinic','doctors')
                  AND ST_DWithin(geom::geography, {PT}::geography, :r))"""),
                    {**base, "r": th.medical_poi_radius_m},
                ).scalar()
            )

    if report.device_id:
        dev = {**base, "dev": report.device_id}
        prev = s.execute(
            text("""
            SELECT ST_Y(geom) AS lat, ST_X(geom) AS lon, reported_at FROM reports
            WHERE device_id = :dev AND id <> :rid AND reported_at <= :t
            ORDER BY reported_at DESC LIMIT 1"""),
            dev,
        ).first()
        if prev:
            ctx.previous_by_device = (float(prev.lat), float(prev.lon), prev.reported_at)
        ctx.device_count_last_hour = s.execute(
            text("""
            SELECT count(*) FROM reports WHERE device_id = :dev AND id <> :rid
              AND reported_at > :t - interval '1 hour' AND reported_at <= :t"""),
            dev,
        ).scalar_one()
    if report.comment and report.comment.strip():
        ctx.same_comment_count_24h = s.execute(
            text("""
            SELECT count(*) FROM reports WHERE commune_id = :cid AND id <> :rid AND comment = :c
              AND reported_at > :t - interval '24 hours' AND reported_at <= :t"""),
            {**base, "c": report.comment},
        ).scalar_one()
    return ctx


def validate_report(
    s: Session, report: Report, lat: float, lon: float, photo: PhotoInfo | None, th: ValidationThresholds
) -> Evaluation:
    """Evaluate and write score/status/rule_hits on the report (no commit)."""
    ctx = build_context(s, report, lat, lon, photo, th)
    ev = evaluate(ctx, th)
    if not report.forced_status:
        report.score = ev.score
        report.status = ev.status
    report.rule_hits = ev.hits_json
    report.duplicate_of = uuid.UUID(ev.duplicate_of) if ev.duplicate_of else None
    if report.device_id and any(h.rule == "R10" for h in ev.hits):
        dev = s.get(Device, report.device_id)
        if dev is not None:
            dev.throttled_until = utcnow() + timedelta(hours=1)
    return ev


def corroborate(s: Session, report: Report, th: ValidationThresholds) -> list[uuid.UUID]:
    """probable -> verified when two independent devices, more than 1 h apart, report the same type within 30 m."""
    if report.status not in ("probable", "verified") or not report.device_id:
        return []
    rows = s.execute(
        text("""
        SELECT o.id FROM reports o, reports r
        WHERE r.id = :rid AND o.id <> r.id AND o.commune_id = r.commune_id
          AND o.status IN ('probable','verified') AND o.waste_type = r.waste_type
          AND o.device_id IS NOT NULL AND o.device_id <> r.device_id
          AND abs(extract(epoch FROM (o.reported_at - r.reported_at))) > 3600
          AND ST_DWithin(o.geom::geography, r.geom::geography, :rad)"""),
        {"rid": report.id, "rad": th.duplicate_radius_m},
    ).all()
    if not rows:
        return []
    ids = [r.id for r in rows] + [report.id]
    promoted = []
    for rep in s.query(Report).filter(Report.id.in_(ids), Report.status == "probable", Report.forced_status.is_(False)):
        rep.status = "verified"
        promoted.append(rep.id)
    return promoted
