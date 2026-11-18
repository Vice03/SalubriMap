# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from salubri_api.models import Base, Timestamped, new_id, utcnow

WASTE_TYPES = ("household", "plastic", "rubble", "organic", "medical", "mixed", "other")
VOLUME_CLASSES = ("bag", "wheelbarrow", "cart", "truck", "more")
REPORT_STATUSES = ("pending", "probable", "verified", "to_review", "rejected", "cleaned")


def _in(col: str, values: tuple[str, ...]) -> str:
    return f"{col} in ({','.join(repr(v) for v in values)})"


class Device(Base):
    __tablename__ = "devices"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reports_count: Mapped[int] = mapped_column(Integer, default=0)
    throttled_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    agent_role: Mapped[str | None] = mapped_column(String(16), nullable=True)


class ImportBatch(Base, Timestamped):
    __tablename__ = "import_batches"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    filename: Mapped[str] = mapped_column(String(256))
    format: Mapped[str] = mapped_column(String(16))
    uploaded_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rows_total: Mapped[int] = mapped_column(Integer, default=0)
    rows_accepted: Mapped[int] = mapped_column(Integer, default=0)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0)
    report: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    rolled_back: Mapped[bool] = mapped_column(Boolean, default=False)


class DumpSite(Base, Timestamped):
    __tablename__ = "dump_sites"
    __table_args__ = (CheckConstraint("status in ('active','cleaned','recurring')", name="ck_dump_status"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    commune_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communes.id", ondelete="CASCADE"), index=True)
    geom: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326))
    hull: Mapped[Any] = mapped_column(Geometry("POLYGON", srid=4326), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    dominant_type: Mapped[str] = mapped_column(String(16))
    volume_est_m3: Mapped[float] = mapped_column(Float, default=0.0)
    n_reports: Mapped[int] = mapped_column(Integer, default=0)
    first_reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cleaned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    near_water: Mapped[bool] = mapped_column(Boolean, default=False)
    near_drain: Mapped[bool] = mapped_column(Boolean, default=False)  # dans ou au bord d'un caniveau (OSM drain/ditch)
    priority: Mapped[float] = mapped_column(Float, default=0.0)
    mean_score: Mapped[float] = mapped_column(Float, default=0.0)
    osm_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class Report(Base, Timestamped):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint(_in("waste_type", WASTE_TYPES), name="ck_report_waste"),
        CheckConstraint(_in("volume_class", VOLUME_CLASSES), name="ck_report_volume"),
        CheckConstraint(_in("status", REPORT_STATUSES), name="ck_report_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    commune_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communes.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[str | None] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)
    client_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    geom: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326))
    gps_accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    waste_type: Mapped[str] = mapped_column(String(16), default="other")
    volume_class: Mapped[str] = mapped_column(String(16), default="bag")
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    score: Mapped[int] = mapped_column(Integer, default=100)
    rule_hits: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    # masquage des visages et plaques : {"client": {faces, plates, manual} | None, "server": n zones}
    masking: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    duplicate_of: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reports.id", ondelete="SET NULL"), nullable=True)
    dump_site_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dump_sites.id", ondelete="SET NULL"), nullable=True, index=True
    )
    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=True, index=True
    )
    quartier_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("quartiers.id", ondelete="SET NULL"), nullable=True
    )
    moderated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    forced_status: Mapped[bool] = mapped_column(Boolean, default=False)


class Photo(Base):
    __tablename__ = "photos"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), index=True)
    path: Mapped[str] = mapped_column(String(256))
    bytes: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    phash: Mapped[str] = mapped_column(String(16))
    phash_b0: Mapped[str] = mapped_column(String(4), index=True)
    phash_b1: Mapped[str] = mapped_column(String(4), index=True)
    phash_b2: Mapped[str] = mapped_column(String(4), index=True)
    phash_b3: Mapped[str] = mapped_column(String(4), index=True)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    exif_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    exif_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    exif_taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    luminance_var: Mapped[float] = mapped_column(Float, default=0.0)
