# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from salubri_api.models import Base, Timestamped, new_id, utcnow

EVENT_KINDS = (
    "reports_changed",
    "fleet_changed",
    "season_changed",
    "zone_changed",
    "budget_changed",
    "frequency_changed",
    "subscription_changed",
    "manual",
)


class Scenario(Base, Timestamped):
    __tablename__ = "scenarios"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    commune_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communes.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scenarios.id", ondelete="SET NULL"), nullable=True)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False)


class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    scenario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(16))
    capacity_t: Mapped[float] = mapped_column(Float)
    cost_per_km: Mapped[float] = mapped_column(Float)
    fixed_cost_day: Mapped[float] = mapped_column(Float)
    out_of_service: Mapped[bool] = mapped_column(Boolean, default=False)
    retired: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )  # retiré de la flotte (historique conservé)
    shift_start: Mapped[int] = mapped_column(Integer, default=300)  # minutes after midnight
    shift_end: Mapped[int] = mapped_column(Integer, default=1080)


class PlanEvent(Base):
    __tablename__ = "plan_events"
    __table_args__ = (
        CheckConstraint("kind in (" + ",".join(repr(k) for k in EVENT_KINDS) + ")", name="ck_event_kind"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    scenario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PlanVersion(Base):
    __tablename__ = "plan_versions"
    __table_args__ = (
        CheckConstraint("status in ('pending','running','ready','failed','superseded')", name="ck_plan_status"),
        CheckConstraint("distance_mode in ('osrm','approx')", name="ck_plan_distance_mode"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    scenario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"), index=True)
    event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plan_events.id", ondelete="SET NULL"), nullable=True)
    event_kind: Mapped[str] = mapped_column(String(32), default="manual")
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    distance_mode: Mapped[str] = mapped_column(String(16), default="approx")
    stages: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    params_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CollectionPoint(Base):
    __tablename__ = "collection_points"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    plan_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plan_versions.id", ondelete="CASCADE"), index=True)
    idx: Mapped[int] = mapped_column(Integer)
    key: Mapped[str] = mapped_column(String(32))  # stable across versions (frozen points keep it)
    geom: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326))
    capacity_t: Mapped[float] = mapped_column(Float)
    demand_t_week: Mapped[float] = mapped_column(Float)
    ilot_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    tw_start: Mapped[int] = mapped_column(Integer, default=420)
    tw_end: Mapped[int] = mapped_column(Integer, default=1020)
    label: Mapped[str] = mapped_column(String(32))
    frozen: Mapped[bool] = mapped_column(Boolean, default=False)


class Route(Base):
    __tablename__ = "routes"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    plan_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plan_versions.id", ondelete="CASCADE"), index=True)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    rotation: Mapped[int] = mapped_column(Integer, default=1)
    distance_km: Mapped[float] = mapped_column(Float)
    duration_min: Mapped[float] = mapped_column(Float)
    load_t: Mapped[float] = mapped_column(Float)
    cost: Mapped[float] = mapped_column(Float)
    geom: Mapped[Any] = mapped_column(Geometry("LINESTRING", srid=4326))


class RouteStop(Base):
    __tablename__ = "route_stops"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    route_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    collection_point_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collection_points.id", ondelete="CASCADE"))
    arrival_min: Mapped[float] = mapped_column(Float)
    load_t_after: Mapped[float] = mapped_column(Float)


class UnservedPoint(Base):
    __tablename__ = "unserved_points"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    plan_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plan_versions.id", ondelete="CASCADE"), index=True)
    collection_point_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collection_points.id", ondelete="CASCADE"))
    demand_t_week: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(64))
