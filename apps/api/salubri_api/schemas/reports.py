# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

WasteType = Literal["household", "plastic", "rubble", "organic", "medical", "mixed", "other"]
VolumeClass = Literal["bag", "wheelbarrow", "cart", "truck", "more"]
ReportStatus = Literal["pending", "probable", "verified", "to_review", "rejected", "cleaned"]


class ReportIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    accuracy: float | None = Field(None, ge=0, description="Précision GPS en mètres")
    waste_type: WasteType = "other"
    volume_class: VolumeClass = "bag"
    comment: str | None = Field(None, max_length=1000)
    reported_at: datetime | None = None
    device_id: str | None = Field(None, max_length=64)
    client_id: str | None = Field(None, max_length=64, description="Identifiant d'idempotence fourni par le client")
    external_id: str | None = Field(None, max_length=128)


class RuleHitOut(BaseModel):
    rule: str
    delta: int
    detail: str
    reject: bool = False


class ReportCreated(BaseModel):
    id: str
    status: ReportStatus
    score: int
    rule_hits: list[RuleHitOut]
    duplicate_of: str | None = None
    already_received: bool = False


class ReportPatch(BaseModel):
    status: Literal["verified", "rejected", "to_review", "probable", "cleaned"]
    note: str | None = None
    actor: str = "moderateur"


class MergeIn(BaseModel):
    into: str = Field(description="Identifiant du signalement ou du dépotoir cible")


class FeatureCollectionOut(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[dict[str, Any]]
    total: int | None = None
