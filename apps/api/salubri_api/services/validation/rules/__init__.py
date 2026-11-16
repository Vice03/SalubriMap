# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validation rules R1-R12. Each rule is pure: it reads a ReportContext and returns a RuleHit or None."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from salubri_api.services.params import ValidationThresholds
from salubri_api.services.validation.photo import PhotoInfo


@dataclass
class Neighbor:
    report_id: str
    distance_m: float
    waste_type: str
    reported_at: datetime
    device_id: str | None
    status: str


@dataclass
class ReportContext:
    """Everything a rule may look at, precomputed by the engine (rules never touch the database)."""

    lat: float
    lon: float
    accuracy_m: float | None
    waste_type: str
    volume_class: str
    comment: str | None
    reported_at: datetime
    device_id: str | None
    photo: PhotoInfo | None = None
    neighbors: list[Neighbor] = field(default_factory=list)
    photo_same_sha: str | None = None  # report id
    photo_similar: tuple[str, int] | None = None  # (report id, hamming)
    in_zone: bool = True
    building_area_m2: float | None = None  # containing building (confidence filtered)
    in_water_area_m2: float | None = None  # containing natural=water polygon
    near_waterway: bool = False
    near_medical_poi: bool = True
    previous_by_device: tuple[float, float, datetime] | None = None  # lat, lon, reported_at
    device_count_last_hour: int = 0
    same_comment_count_24h: int = 0
    same_point_other_device: str | None = None


@dataclass
class RuleHit:
    rule: str
    delta: int
    detail: str
    reject: bool = False
    duplicate_of: str | None = None

    def as_dict(self) -> dict[str, object]:
        d: dict[str, object] = {"rule": self.rule, "delta": self.delta, "detail": self.detail}
        if self.reject:
            d["reject"] = True
        return d


class Rule(Protocol):
    code: str
    title: str
    description: str
    penalty: str

    def apply(self, ctx: ReportContext, th: ValidationThresholds) -> RuleHit | None: ...


def all_rules() -> list[Rule]:
    from salubri_api.services.validation.rules.r01_duplicate import R01Duplicate
    from salubri_api.services.validation.rules.r02_photo_reuse import R02PhotoReuse
    from salubri_api.services.validation.rules.r03_exif_location import R03ExifLocation
    from salubri_api.services.validation.rules.r04_exif_date import R04ExifDate
    from salubri_api.services.validation.rules.r05_out_of_zone import R05OutOfZone
    from salubri_api.services.validation.rules.r06_in_building import R06InBuilding
    from salubri_api.services.validation.rules.r07_in_water import R07InWater
    from salubri_api.services.validation.rules.r08_fake_gps import R08FakeGps
    from salubri_api.services.validation.rules.r09_impossible_speed import R09ImpossibleSpeed
    from salubri_api.services.validation.rules.r10_spam import R10Spam
    from salubri_api.services.validation.rules.r11_uninformative_photo import R11UninformativePhoto
    from salubri_api.services.validation.rules.r12_type_consistency import R12TypeConsistency

    return [
        R01Duplicate(),
        R02PhotoReuse(),
        R03ExifLocation(),
        R04ExifDate(),
        R05OutOfZone(),
        R06InBuilding(),
        R07InWater(),
        R08FakeGps(),
        R09ImpossibleSpeed(),
        R10Spam(),
        R11UninformativePhoto(),
        R12TypeConsistency(),
    ]
