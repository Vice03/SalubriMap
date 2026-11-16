# SPDX-License-Identifier: AGPL-3.0-or-later
from pydantic import BaseModel, Field


class SimulateIn(BaseModel):
    seed: int | None = None
    horizon_days: int | None = Field(None, ge=7, le=365)
    replications: int = Field(5, ge=1, le=20)
