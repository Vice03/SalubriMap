# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests: one positive and one negative case per rule, on pure ReportContext objects."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from salubri_api.services.params import ValidationThresholds
from salubri_api.services.validation.engine import evaluate
from salubri_api.services.validation.photo import PhotoInfo
from salubri_api.services.validation.rules import Neighbor, ReportContext
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

TH = ValidationThresholds()
T = datetime(2026, 11, 15, 12, tzinfo=UTC)
PHOTO = PhotoInfo("a" * 64, "f0f0f0f0f0f0f0f0", 640, 480, 120_000, None, None, None, 900.0)
BASE = ReportContext(
    lat=12.3512345,
    lon=-1.5212345,
    accuracy_m=8,
    waste_type="household",
    volume_class="cart",
    comment=None,
    reported_at=T,
    device_id="d1",
    photo=PHOTO,
)


def nb(dist: float, hours: float, device: str = "d1", wt: str = "household") -> Neighbor:
    return Neighbor("r-old", dist, wt, T - timedelta(hours=hours), device, "probable")


def test_clean_context_scores_100():
    ev = evaluate(BASE, TH)
    assert ev.score == 100 and ev.status == "probable" and ev.hits == []


@pytest.mark.parametrize(
    "ctx,hit",
    [
        (replace(BASE, neighbors=[nb(12, 5)]), True),  # same device, 5 h
        (replace(BASE, neighbors=[nb(12, 0.5, "d2")]), True),  # other device, 30 min: burst
        (replace(BASE, neighbors=[nb(12, 5, "d2")]), False),  # other device, 5 h: corroboration
        (replace(BASE, neighbors=[nb(45, 5)]), False),  # too far
        (replace(BASE, neighbors=[nb(12, 5, wt="rubble")]), False),  # other type
    ],
)
def test_r1(ctx, hit):
    h = R01Duplicate().apply(ctx, TH)
    assert (h is not None) == hit
    if h:
        assert h.delta == -40 and h.duplicate_of == "r-old"


def test_r2():
    assert R02PhotoReuse().apply(replace(BASE, photo_same_sha="x" * 36), TH).delta == -70
    assert R02PhotoReuse().apply(replace(BASE, photo_similar=("x" * 36, 6)), TH).delta == -50
    assert R02PhotoReuse().apply(replace(BASE, photo_similar=("x" * 36, 20)), TH) is None
    assert R02PhotoReuse().apply(BASE, TH) is None


def test_r3_r4():
    far = replace(PHOTO, exif_lat=12.37, exif_lon=-1.52)
    near = replace(PHOTO, exif_lat=12.3513, exif_lon=-1.5212)
    assert R03ExifLocation().apply(replace(BASE, photo=far), TH).delta == -30
    assert R03ExifLocation().apply(replace(BASE, photo=near), TH) is None
    old = replace(PHOTO, exif_taken_at=T - timedelta(days=400))
    assert R04ExifDate().apply(replace(BASE, photo=old), TH).delta == -20
    assert R04ExifDate().apply(replace(BASE, photo=replace(PHOTO, exif_taken_at=T - timedelta(days=2))), TH) is None


def test_r5_rejects():
    h = R05OutOfZone().apply(replace(BASE, in_zone=False), TH)
    assert h.reject and evaluate(replace(BASE, in_zone=False), TH).status == "rejected"
    assert R05OutOfZone().apply(BASE, TH) is None


def test_r6():
    assert R06InBuilding().apply(replace(BASE, building_area_m2=120), TH).delta == -35
    assert R06InBuilding().apply(replace(BASE, building_area_m2=500), TH).delta == -50
    assert R06InBuilding().apply(replace(BASE, building_area_m2=20), TH) is None


def test_r7():
    assert R07InWater().apply(replace(BASE, in_water_area_m2=50_000), TH).reject
    assert R07InWater().apply(replace(BASE, in_water_area_m2=500), TH).delta == -45
    assert R07InWater().apply(replace(BASE, near_waterway=True), TH).delta == -45
    assert R07InWater().apply(BASE, TH) is None


def test_r8():
    assert R08FakeGps().apply(replace(BASE, lat=0.0, lon=0.0), TH).reject
    assert R08FakeGps().apply(replace(BASE, lat=12.37, lon=-1.52), TH).delta == -25
    assert R08FakeGps().apply(replace(BASE, same_point_other_device="r" * 36), TH).delta == -40
    assert R08FakeGps().apply(replace(BASE, accuracy_m=900), TH).delta == -15
    assert R08FakeGps().apply(BASE, TH) is None


def test_r9():
    prev = (12.45, -1.52, T - timedelta(minutes=3))
    assert R09ImpossibleSpeed().apply(replace(BASE, previous_by_device=prev), TH).delta == -40
    slow = (12.45, -1.52, T - timedelta(hours=2))
    assert R09ImpossibleSpeed().apply(replace(BASE, previous_by_device=slow), TH) is None


def test_r10():
    assert R10Spam().apply(replace(BASE, device_count_last_hour=12), TH).delta == -30
    assert R10Spam().apply(replace(BASE, comment="tas", same_comment_count_24h=4), TH).delta == -30
    assert R10Spam().apply(replace(BASE, device_count_last_hour=3), TH) is None


def test_r11():
    assert R11UninformativePhoto().apply(replace(BASE, photo=replace(PHOTO, luminance_var=1.0)), TH).delta == -20
    assert R11UninformativePhoto().apply(replace(BASE, photo=replace(PHOTO, width=120, height=90)), TH).delta == -20
    assert R11UninformativePhoto().apply(BASE, TH) is None


def test_r12():
    light = replace(PHOTO, bytes=20_000)
    assert R12TypeConsistency().apply(replace(BASE, volume_class="truck", photo=light), TH).delta == -10
    assert R12TypeConsistency().apply(replace(BASE, waste_type="medical", near_medical_poi=False), TH).delta == -10
    assert R12TypeConsistency().apply(BASE, TH) is None


def test_scoring_thresholds():
    assert evaluate(replace(BASE, building_area_m2=120), TH).status == "to_review"  # 65
    combined = replace(BASE, building_area_m2=500, photo_same_sha="z" * 36)
    assert evaluate(combined, TH).status == "rejected"  # 100 - 50 - 70
