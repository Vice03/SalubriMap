# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from salubri_api.models import Base, Timestamped, new_id


class Quartier(Base, Timestamped):
    __tablename__ = "quartiers"
    __table_args__ = (CheckConstraint("source in ('demo','jury','osm','user')", name="ck_quartier_source"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    commune_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("communes.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    arrondissement: Mapped[int | None] = mapped_column(Integer, nullable=True)
    population: Mapped[int] = mapped_column(Integer, default=0)
    geom: Mapped[Any] = mapped_column(Geometry("MULTIPOLYGON", srid=4326))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(16), default="demo")


class Ilot(Base):
    """A block of ~30 buildings: the household unit of the simulation."""

    __tablename__ = "ilots"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    quartier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quartiers.id", ondelete="CASCADE"), index=True)
    geom: Mapped[Any] = mapped_column(Geometry("POLYGON", srid=4326))
    centroid: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326))
    n_buildings: Mapped[int] = mapped_column(Integer, default=0)
    population: Mapped[float] = mapped_column(Float, default=0.0)
    demand_kg_day: Mapped[float] = mapped_column(Float, default=0.0)
    near_water: Mapped[bool] = mapped_column(Boolean, default=False)
