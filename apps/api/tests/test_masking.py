# SPDX-License-Identifier: AGPL-3.0-or-later
"""Masquage côté serveur : seconde passe sur chaque photo (envoi, import), refus sans modèles, rattrapage."""

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from conftest import free_point
from salubri_api.config import get_settings
from salubri_api.models import Photo, Report
from salubri_api.services.masking import detector
from salubri_api.services.masking.backfill import backfill
from salubri_api.services.masking.detector import Box, detect, pixelate

PHOTO = (Path(__file__).parent / "fixtures" / "visage_et_plaque.jpg").read_bytes()
FACE, PLATE = (181, 67, 88, 107), (842, 197, 182, 69)  # référence (onnxruntime) dans cette image 1309×512


def _textured(img: Image.Image, box: tuple[int, int, int, int]) -> float:
    """Part des pixels où le laplacien de la luminance dépasse 12 : ~0,6 sur un visage, faible si pixellisé."""
    x, y, w, h = box
    g = np.asarray(img.convert("L"), dtype=np.float32)[y : y + h, x : x + w]
    lap = np.abs(4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:])
    return float((lap > 12).mean())


def _stored(db, rid) -> Image.Image:  # type: ignore[no-untyped-def]
    ph = db.query(Photo).filter(Photo.report_id == rid).one()
    return Image.open(get_settings().photos_dir / ph.path)


def test_detector_finds_the_reference_boxes() -> None:
    boxes = detect(Image.open(io.BytesIO(PHOTO)).convert("RGB"))
    kinds = sorted(b.kind for b in boxes)
    assert kinds == ["plaque", "visage"]
    face = next(b for b in boxes if b.kind == "visage")
    assert abs(face.x - FACE[0]) < 4 and abs(face.w - FACE[2]) < 4


def test_pixelate_leaves_no_original_pixel() -> None:
    rng = np.random.default_rng(1)
    orig = rng.integers(0, 256, (120, 160, 3), dtype=np.uint8)
    arr = orig.copy()
    assert pixelate(arr, [Box(40, 30, 50, 40, "visage", 0.9)]) == 1
    zone = arr[22:78, 30:100]
    assert len({tuple(p) for p in zone.reshape(-1, 3)}) <= 36  # 6×6 aplats au plus
    assert (zone == orig[22:78, 30:100]).all(axis=2).mean() < 0.001
    assert (arr[:20] == orig[:20]).all()  # hors zone intact


def test_unmasked_upload_is_masked_before_storage(db, client, world):  # type: ignore[no-untyped-def]
    lon, lat = free_point(world, n=70)
    r = client.post(
        "/api/reports",
        data={"lon": str(lon), "lat": str(lat), "device_id": "m-1"},
        files={"photo": ("vieille-app.jpg", PHOTO, "image/jpeg")},
    )
    assert r.status_code == 201, r.text
    rep = db.get(Report, r.json()["id"])
    assert rep.masking == {"client": None, "server": 2}
    img = _stored(db, rep.id)
    assert img.size == (1309, 512)
    orig = Image.open(io.BytesIO(PHOTO))
    for box in (FACE, PLATE):
        assert _textured(img, box) < 0.4 * _textured(orig, box)


def test_photo_already_masked_on_the_phone_counts_zero_on_server(db, client, world):  # type: ignore[no-untyped-def]
    arr = np.array(Image.open(io.BytesIO(PHOTO)).convert("RGB"))
    pixelate(arr, [Box(*FACE, "visage", 1), Box(*PLATE, "plaque", 1)])  # comme Salubri Go
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, "JPEG", quality=88)
    lon, lat = free_point(world, n=71)
    r = client.post(
        "/api/reports",
        data={
            "lon": str(lon),
            "lat": str(lat),
            "device_id": "m-2",
            "masking_client": json.dumps({"faces": 1, "plates": 1, "manual": 0}),
        },
        files={"photo": ("p.jpg", buf.getvalue(), "image/jpeg")},
    )
    rep = db.get(Report, r.json()["id"])
    assert rep.masking == {"client": {"faces": 1, "plates": 1, "manual": 0}, "server": 0}


def test_zip_import_photos_are_masked(db, client):  # type: ignore[no-untyped-def]
    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-1.52, 12.37]},
                "properties": {"photo": "rue.jpg", "id": "zip-m-1", "type": "menager"},
            }
        ],
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("jury.geojson", json.dumps(fc))
        z.writestr("photos/rue.jpg", PHOTO)
    r = client.post("/api/imports", files={"file": ("jury.zip", buf.getvalue(), "application/zip")})
    assert r.status_code == 200, r.text
    rep = db.query(Report).filter(Report.external_id == "zip-m-1").one()
    assert rep.masking["server"] == 2
    assert _textured(_stored(db, rep.id), FACE) < 0.25


def test_without_models_no_photo_is_stored(db, client, world, monkeypatch, tmp_path):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(get_settings(), "masking_models_dir", tmp_path)  # dossier vide
    detector._sessions.cache_clear()
    try:
        lon, lat = free_point(world, n=72)
        r = client.post(
            "/api/reports",
            data={"lon": str(lon), "lat": str(lat), "device_id": "m-3", "client_id": "m-3"},
            files={"photo": ("p.jpg", PHOTO, "image/jpeg")},
        )
        assert r.status_code == 503 and "Masquage" in r.json()["detail"]
        assert db.query(Report).filter(Report.client_id == "m-3").count() == 0
        assert client.get("/api/health").json()["masking"] == "indisponible"
    finally:
        monkeypatch.undo()
        detector._sessions.cache_clear()
    assert client.get("/api/health").json()["masking"] == "ok"


def test_backfill_masks_photos_stored_before(db, client, world, monkeypatch):  # type: ignore[no-untyped-def]
    from salubri_api.services.validation import photo as photo_mod

    real = photo_mod.reencode
    monkeypatch.setattr(photo_mod, "reencode", lambda data, mask=True: real(data, mask=False))  # « ancienne version »
    lon, lat = free_point(world, n=73)
    rid = client.post(
        "/api/reports",
        data={"lon": str(lon), "lat": str(lat), "device_id": "m-4"},
        files={"photo": ("p.jpg", PHOTO, "image/jpeg")},
    ).json()["id"]
    monkeypatch.setattr(photo_mod, "reencode", real)
    assert _textured(_stored(db, rid), FACE) > 0.4  # stockée en clair
    assert backfill(db, dry_run=True)["masquees"] >= 1
    first = backfill(db)
    assert first["zones"] >= 2
    db.expire_all()
    assert _textured(_stored(db, rid), FACE) < 0.25
    assert db.get(Report, rid).masking["rattrapage"] is True
    assert backfill(db)["masquees"] == 0  # rejouable : plus rien à masquer


@pytest.mark.parametrize("raw", ["pas du json", "[1,2]", '{"faces": "x"}'])
def test_bad_masking_client_is_ignored(db, client, world, raw):  # type: ignore[no-untyped-def]
    lon, lat = free_point(world, n=74)
    r = client.post(
        "/api/reports",
        data={"lon": str(lon), "lat": str(lat), "device_id": "m-5", "masking_client": raw},
        files={"photo": ("p.jpg", PHOTO, "image/jpeg")},
    )
    assert r.status_code == 201
    assert db.get(Report, r.json()["id"]).masking["client"] is None
