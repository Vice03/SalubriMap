# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from salubri_api.models import Base, new_id


class Building(Base):
    __tablename__ = "buildings"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    commune_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communes.id", ondelete="CASCADE"), index=True)
    geom: Mapped[Any] = mapped_column(Geometry("POLYGON", srid=4326))
    area_m2: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str] = mapped_column(String(32), default="open_buildings")
    ilot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)


class Water(Base):
    __tablename__ = "water"
    __table_args__ = (CheckConstraint("kind in ('water','waterway','wetland')", name="ck_water_kind"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    commune_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communes.id", ondelete="CASCADE"), index=True)
    geom: Mapped[Any] = mapped_column(Geometry("GEOMETRY", srid=4326))
    kind: Mapped[str] = mapped_column(String(16))
    subkind: Mapped[str | None] = mapped_column(String(16), nullable=True)  # étiquette OSM waterway (drain = caniveau)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    area_m2: Mapped[float] = mapped_column(Float, default=0.0)
    flood_prone: Mapped[bool] = mapped_column(Boolean, default=False)


class Road(Base):
    __tablename__ = "roads"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    commune_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communes.id", ondelete="CASCADE"), index=True)
    osm_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    geom: Mapped[Any] = mapped_column(Geometry("LINESTRING", srid=4326))
    highway: Mapped[str] = mapped_column(String(32))
    surface: Mapped[str | None] = mapped_column(String(32), nullable=True)
    truck_ok: Mapped[bool] = mapped_column(Boolean, default=True)


class Poi(Base):
    """Points of interest used by rules and exclusions: hospitals, schools, markets."""

    __tablename__ = "pois"
    __table_args__ = (
        CheckConstraint(
            "kind in ('hospital','clinic','doctors','school','marketplace','cemetery','military')", name="ck_poi_kind"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    commune_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communes.id", ondelete="CASCADE"), index=True)
    geom: Mapped[Any] = mapped_column(Geometry("GEOMETRY", srid=4326))
    kind: Mapped[str] = mapped_column(String(16))
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
