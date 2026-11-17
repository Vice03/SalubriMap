# SPDX-License-Identifier: AGPL-3.0-or-later
"""Report ingestion shared by the API (Salubri Go) and file imports."""

import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from shapely.geometry import Point
from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api.config import get_settings
from salubri_api.models import Commune, Device, Photo, Report, utcnow
from salubri_api.schemas.reports import ReportIn
from salubri_api.services.geo import to_wkb
from salubri_api.services.params import ValidationThresholds
from salubri_api.services.validation.engine import Evaluation, corroborate, validate_report
from salubri_api.services.validation.photo import PhotoInfo, analyze, store


def thresholds_for(commune: Commune) -> ValidationThresholds:
    return ValidationThresholds(**(commune.params_default or {}).get("validation", {}))


def _touch_device(s: Session, device_id: str | None) -> None:
    if not device_id:
        return
    dev = s.get(Device, device_id)
    if dev is None:
        s.add(Device(id=device_id, reports_count=1))
    else:
        dev.reports_count += 1
        dev.last_seen = utcnow()


@dataclass
class Staged:
    report: Report
    lat: float
    lon: float
    photo: PhotoInfo | None


def stage_report(
    s: Session, commune: Commune, data: ReportIn, photo_bytes: bytes | None, import_batch_id: uuid.UUID | None = None
) -> Staged:
    """Insert a report (and its photo) without validating it. Raises ValueError on an unreadable photo."""
    info = analyze(photo_bytes) if photo_bytes else None
    if info is not None and info.exif_lat is None and info.exif_taken_at is None:
        # photo masquée sur le téléphone (sans EXIF) : on reprend les valeurs lues avant le masquage
        taken = data.exif_taken_at
        if taken is not None and taken.tzinfo is None:
            taken = taken.replace(tzinfo=UTC)
        info = replace(info, exif_lat=data.exif_lat, exif_lon=data.exif_lon, exif_taken_at=taken)
    _touch_device(s, data.device_id)
    reported_at = data.reported_at or datetime.now(UTC)
    if reported_at.tzinfo is None:
        reported_at = reported_at.replace(tzinfo=UTC)
    rep = Report(
        commune_id=commune.id,
        device_id=data.device_id,
        client_id=data.client_id,
        external_id=data.external_id,
        geom=to_wkb(Point(data.lon, data.lat)),
        gps_accuracy_m=data.accuracy,
        waste_type=data.waste_type,
        volume_class=data.volume_class,
        comment=(data.comment or None),
        reported_at=reported_at,
        import_batch_id=import_batch_id,
        status="pending",
        score=100,
        rule_hits=[],
    )
    s.add(rep)
    s.flush()
    rep.quartier_id = s.execute(
        text("""SELECT id FROM quartiers WHERE commune_id = :c
        AND ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)) LIMIT 1"""),
        {"c": commune.id, "lon": data.lon, "lat": data.lat},
    ).scalar()
    if info is not None and photo_bytes is not None:
        path = store(photo_bytes, info, get_settings().photos_dir)
        b = info.bands
        s.add(
            Photo(
                report_id=rep.id,
                path=path,
                bytes=info.bytes,
                sha256=info.sha256,
                phash=info.phash,
                phash_b0=b[0],
                phash_b1=b[1],
                phash_b2=b[2],
                phash_b3=b[3],
                width=info.width,
                height=info.height,
                exif_lat=info.exif_lat,
                exif_lon=info.exif_lon,
                exif_taken_at=info.exif_taken_at,
                luminance_var=info.luminance_var,
            )
        )
    s.flush()
    return Staged(rep, data.lat, data.lon, info)


def validate_staged(s: Session, commune: Commune, staged: list[Staged]) -> dict[uuid.UUID, Evaluation]:
    """Validate in chronological order so that 'earlier evidence' is well defined."""
    th = thresholds_for(commune)
    out: dict[uuid.UUID, Evaluation] = {}
    for st in sorted(staged, key=lambda x: (x.report.reported_at, x.report.received_at)):
        out[st.report.id] = validate_report(s, st.report, st.lat, st.lon, st.photo, th)
        s.flush()
    for st in staged:
        corroborate(s, st.report, th)
    s.flush()
    return out


def find_by_client_id(s: Session, client_id: str | None) -> Report | None:
    if not client_id:
        return None
    return s.query(Report).filter(Report.client_id == client_id).first()
