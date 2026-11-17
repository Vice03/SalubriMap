# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tables du module « Saisons » : état des routes par période, lots d'import, signalements « Route impraticable »."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from salubri_api.modules.seasons.interface import Base

SOURCES = ("import", "report", "manual")


def _now() -> datetime:
    return datetime.now(UTC)


class RoadImportBatch(Base):
    __tablename__ = "road_import_batches"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commune_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communes.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(200))
    rows: Mapped[int] = mapped_column(Integer, default=0)
    accepted: Mapped[int] = mapped_column(Integer, default=0)
    report: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RoadCondition(Base):
    """État d'une route pour une période (« dry », « rain » ou une phase du calendrier de la commune)."""

    __tablename__ = "road_conditions"
    __table_args__ = (UniqueConstraint("road_id", "period", "source", name="uq_road_condition"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    road_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roads.id", ondelete="CASCADE"), index=True)
    period: Mapped[str] = mapped_column(String(32), index=True)
    passable: Mapped[bool] = mapped_column(Boolean, default=True)
    speed_factor: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str] = mapped_column(String(16), default="manual")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("road_import_batches.id", ondelete="CASCADE"), nullable=True, index=True
    )


class RoadReport(Base):
    """Signalement « Route impraticable » de Salubri Go : un signalement ordinaire (règles, masquage) relié à la
    route la plus proche. Il ne devient un état de route qu'une fois vérifié par un modérateur."""

    __tablename__ = "road_reports"
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True)
    road_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("roads.id", ondelete="SET NULL"), nullable=True)
    period: Mapped[str] = mapped_column(String(32), default="rain")
    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
