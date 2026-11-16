# SPDX-License-Identifier: AGPL-3.0-or-later
"""SQLAlchemy models. Geometries are SRID 4326, column name `geom`."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> uuid.UUID:
    return uuid.uuid4()


class Base(DeclarativeBase):
    pass


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


from salubri_api.models.audit import AuditLog  # noqa: E402
from salubri_api.models.buildings import Building, Poi, Road, Water  # noqa: E402
from salubri_api.models.communes import Commune  # noqa: E402
from salubri_api.models.plans import (  # noqa: E402
    CollectionPoint,
    PlanEvent,
    PlanVersion,
    Route,
    RouteStop,
    Scenario,
    UnservedPoint,
    Vehicle,
)
from salubri_api.models.quartiers import Ilot, Quartier  # noqa: E402
from salubri_api.models.reports import Device, DumpSite, ImportBatch, Photo, Report  # noqa: E402
from salubri_api.models.sim import SimRun  # noqa: E402

__all__ = [
    "AuditLog",
    "Base",
    "Building",
    "Poi",
    "CollectionPoint",
    "Commune",
    "Device",
    "DumpSite",
    "Ilot",
    "ImportBatch",
    "Photo",
    "PlanEvent",
    "PlanVersion",
    "Quartier",
    "Report",
    "Road",
    "Route",
    "RouteStop",
    "Scenario",
    "SimRun",
    "Timestamped",
    "UnservedPoint",
    "Vehicle",
    "Water",
    "new_id",
    "utcnow",
]
