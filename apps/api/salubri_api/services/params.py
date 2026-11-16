# SPDX-License-Identifier: AGPL-3.0-or-later
"""Scenario parameters (validated JSON stored in scenarios.params) and validation thresholds."""

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ValidationThresholds(BaseModel):
    model_config = ConfigDict(extra="ignore")

    duplicate_radius_m: float = 30
    duplicate_window_h: float = 72
    phash_max_hamming: int = 8
    exif_gps_max_m: float = 500
    exif_max_age_days: float = 30
    zone_buffer_m: float = 500
    building_min_confidence: float = 0.7
    building_small_m2: float = 40
    building_large_m2: float = 200
    waterway_buffer_m: float = 8
    big_water_m2: float = 10_000
    gps_accuracy_max_m: float = 150
    same_point_m: float = 1
    max_speed_kmh: float = 120
    spam_per_hour: int = 10
    spam_same_comment: int = 5
    luminance_var_min: float = 25
    photo_min_side_px: int = 200
    truck_photo_min_bytes: int = 50_000
    medical_poi_radius_m: float = 300
    probable_min: int = 70
    review_min: int = 40


class ScenarioParams(BaseModel):
    """Everything the planner can change. Every field has a default so partial PATCHes are safe."""

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def _legacy_keys(cls, data: Any) -> Any:
        # avant v0.2, le nettoyage était (à tort) attribué à la brigade Laabal
        if isinstance(data, dict) and "laabal_capacity_t_day" in data and "cleanup_capacity_t_day" not in data:
            data = {**data, "cleanup_capacity_t_day": data["laabal_capacity_t_day"]}
        return data

    population_factor: float = Field(1.0, ge=0.1, le=5)
    waste_kg_per_person_day: float = Field(0.6, gt=0, le=3)
    subscription_rate: float = Field(0.35, ge=0, le=1)
    subscription_fee_fcfa_month: float = Field(1500, ge=0)
    precollector_capacity_t: float = Field(1.2, gt=0)
    precollector_frequency_per_week: float = Field(2, ge=0, le=7)
    precollector_cost_fcfa_month: float = Field(60000, ge=0)
    collection_point_capacity_t: float = Field(2.5, gt=0)
    collection_point_max: int = Field(80, ge=1, le=500)
    pickup_frequency_per_week: float = Field(2, gt=0, le=7)
    walk_distance_max_m: float = Field(300, gt=0)
    season: Literal["dry", "rain"] = "dry"
    flood_speed_factor: float = Field(0.7, gt=0, le=1)
    truck_breakdown_rate_per_day: float = Field(0.02, ge=0, le=1)
    budget_fcfa_month: float = Field(25_000_000, ge=0)
    fuel_cost_fcfa_per_km: float = Field(450, ge=0)
    # Nettoyage des dépotoirs : services techniques de la mairie (la brigade Laabal ne ramasse pas).
    cleanup_capacity_t_day: float = Field(12, ge=0)
    # Brigade Laabal (police civique) : contrôles, sensibilisation, sanctions -> dissuasion.
    laabal_operations_per_week: float = Field(3, ge=0, le=14)
    laabal_deterrence: float = Field(0.5, ge=0, le=1)
    use_existing_cct: bool = True  # CCT existants (SDGD 2020) gardés comme points de regroupement
    active_quartier_ids: list[str] | None = None
    horizon_days: int = Field(90, ge=7, le=365)
    seed: int = 42
    vrp_time_limit_s: float = Field(1.0, gt=0, le=30)
    ilot_size_buildings: int = Field(30, ge=5, le=500)


# Which event a parameter change triggers (pipeline invalidation, see services/plan/events.py).
PARAM_EVENT: dict[str, str] = {
    "population_factor": "frequency_changed",
    "waste_kg_per_person_day": "frequency_changed",
    "active_quartier_ids": "zone_changed",
    "use_existing_cct": "manual",
    "ilot_size_buildings": "zone_changed",
    "collection_point_capacity_t": "frequency_changed",
    "collection_point_max": "frequency_changed",
    "pickup_frequency_per_week": "frequency_changed",
    "walk_distance_max_m": "frequency_changed",
    "season": "season_changed",
    "flood_speed_factor": "season_changed",
    "budget_fcfa_month": "budget_changed",
    "fuel_cost_fcfa_per_km": "budget_changed",
    "cleanup_capacity_t_day": "budget_changed",
    "laabal_operations_per_week": "budget_changed",
    "laabal_deterrence": "budget_changed",
    "truck_breakdown_rate_per_day": "budget_changed",
    "subscription_rate": "subscription_changed",
    "subscription_fee_fcfa_month": "subscription_changed",
    "precollector_capacity_t": "subscription_changed",
    "precollector_frequency_per_week": "subscription_changed",
    "precollector_cost_fcfa_month": "subscription_changed",
    "horizon_days": "subscription_changed",
    "seed": "subscription_changed",
    "vrp_time_limit_s": "fleet_changed",
}

# Breadth order: when several keys change at once, the widest event wins.
EVENT_BREADTH = [
    "subscription_changed",
    "budget_changed",
    "fleet_changed",
    "season_changed",
    "frequency_changed",
    "reports_changed",
    "zone_changed",
    "manual",
]


def widest_event(kinds: set[str]) -> str:
    return max(kinds, key=EVENT_BREADTH.index) if kinds else "manual"


def load_params_file(path: Path) -> dict[str, Any]:
    if path.exists():
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data
    return {}
