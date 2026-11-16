# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from salubri_api.models import Base, Timestamped, new_id


class Commune(Base, Timestamped):
    __tablename__ = "communes"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    bbox: Mapped[Any] = mapped_column(Geometry("POLYGON", srid=4326))
    depot_geom: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326))
    params_default: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
