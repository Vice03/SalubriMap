# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Any

from pydantic import BaseModel, Field


class VehicleIn(BaseModel):
    id: str | None = None
    label: str | None = None
    kind: str | None = None
    capacity_t: float | None = Field(None, gt=0)
    cost_per_km: float | None = Field(None, ge=0)
    fixed_cost_day: float | None = Field(None, ge=0)
    out_of_service: bool | None = None


class ScenarioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    parent_id: str | None = None
    params: dict[str, Any] = {}
    # taille de flotte voulue : des bennes 8 t sont ajoutées si le parent en a moins (implantations ville entière)
    trucks: int | None = Field(None, ge=1, le=200)


class ScenarioPatch(BaseModel):
    name: str | None = None
    params: dict[str, Any] = {}
    vehicles: list[VehicleIn] | None = None


class BreakdownIn(BaseModel):
    out_of_service: bool = True


class RecomputeIn(BaseModel):
    reason: str | None = None
