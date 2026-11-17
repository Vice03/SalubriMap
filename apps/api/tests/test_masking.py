# SPDX-License-Identifier: AGPL-3.0-or-later
"""Masquage côté serveur : seconde passe sur chaque photo (envoi, import), photo privée si la détection échoue,
mode manuel en modération, rattrapage."""

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
    # décodage exact sur l'image entière (même référence qu'avant les tuiles) …
    face_s, _ = detector._sessions(str(get_settings().masking_models_dir))
    whole = detector._faces(face_s, Image.open(io.BytesIO(PHOTO)).convert("RGB"))
    assert len(whole) >= 1 and abs(whole[0].x - FACE[0]) < 4 and abs(whole[0].w - FACE[2]) < 4
    # … et après fusion avec les tuiles, la boîte gardée recouvre la même tête
    face = next(b for b in boxes if b.kind == "visage")
    ref = Box(*FACE, kind="visage", score=1.0)
    assert detector._iou(face, ref) > 0.8


def test_tiles_same_as_phone() -> None:
    """Même découpe que apps/go/src/__tests__/masking.test.ts ('même découpe que le serveur')."""
    from salubri_api.services.masking.detector import tiles

    assert tiles(600, 400, 640) == []
    assert tiles(800, 600, 640) == [(0, 0, 640, 600), (160, 0, 800, 600)]
    assert tiles(1309, 512, 640) == [(0, 0, 640, 512), (512, 0, 1152, 512), (669, 0, 1309, 512)]
    assert tiles(1309, 512, 576) == [(0, 0, 576, 512), (460, 0, 1036, 512), (733, 0, 1309, 512)]
    big = tiles(1920, 1440, 640)
    assert len(big) == 12 and big[:3] == [(0, 0, 640, 640), (0, 512, 640, 1152), (0, 800, 640, 1440)]
    # recouvrement : chaque pixel est dans une tuile
    cov = np.zeros((1440, 1920), bool)
    for x0, y0, x1, y1 in big:
        cov[y0:y1, x0:x1] = True
    assert cov.all()


def test_tiles_merge_boxes_back_without_duplicates(monkeypatch) -> None:
    """Une tête vue par l'image entière et par deux tuiles ne donne qu'une boîte, aux coordonnées de l'image."""
    from salubri_api.services.masking import detector as d

    def fake_faces(_sess, img):  # type: ignore[no-untyped-def]
        # le visage est au pixel (700, 300)-(730, 330) de l'image de travail ; chaque vue le rend dans son repère
        ox, oy = getattr(img, "_ox", 0), getattr(img, "_oy", 0)
        return [d.Box(700 - ox, 300 - oy, 30, 30, "visage", 0.9)] if ox <= 700 <= ox + img.width else []

    real_crop = Image.Image.crop

    def crop(self, box):  # type: ignore[no-untyped-def]
        out = real_crop(self, box)
        out._ox, out._oy = box[0], box[1]
        return out

    monkeypatch.setattr(d, "_faces", fake_faces)
    monkeypatch.setattr(d, "_plates", lambda *_a: [])
    monkeypatch.setattr(Image.Image, "crop", crop)
    boxes = d.detect(Image.new("RGB", (1200, 512)))  # ≤ WORK_MAX_SIDE : pas de mise à l'échelle
    assert [(round(b.x), round(b.y)) for b in boxes] == [(700, 300)]


def test_small_background_face_needs_the_tiles() -> None:
    img = Image.open(Path(__file__).parent / "fixtures" / "petit_visage.jpg").convert("RGB")
    face_s, _ = detector._sessions(str(get_settings().masking_models_dir))
    assert detector._faces(face_s, img.resize((1280, 853))) == []  # image de travail entière seule : manqué
    found = [b for b in detect(img) if b.kind == "visage"]
    assert len(found) == 1 and abs(found[0].x - 1700) < 15 and abs(found[0].y - 500) < 15


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
    assert rep.masking == {"client": None, "server": 2, "mode": "inconnu"}  # ancien client : mode non annoncé
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
    assert rep.masking == {
        "client": {"faces": 1, "plates": 1, "manual": 0, "mode": "auto"},
        "server": 0,
        "mode": "auto",
    }


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


def test_without_models_photo_kept_private_and_report_flagged(db, client, world, monkeypatch, tmp_path):  # type: ignore[no-untyped-def]
    """Lot 2.3 : détection du serveur impossible → photo dans le dossier privé, jamais publique, signalement à
    vérifier ; le rattrapage la masque et la sort du dossier privé quand les modèles reviennent."""
    monkeypatch.setattr(get_settings(), "masking_models_dir", tmp_path)  # dossier vide
    detector._sessions.cache_clear()
    try:
        lon, lat = free_point(world, n=72)
        r = client.post(
            "/api/reports",
            data={"lon": str(lon), "lat": str(lat), "device_id": "m-3", "client_id": "m-3"},
            files={"photo": ("p.jpg", PHOTO, "image/jpeg")},
        )
        assert r.status_code == 201, r.text
        rep = db.query(Report).filter(Report.client_id == "m-3").one()
        assert rep.masking["server"] is None and "modèles indisponibles" in rep.masking["erreur_serveur"]
        assert rep.status == "to_review" and any(h["rule"] == "M0" for h in rep.rule_hits)
        ph = db.query(Photo).filter(Photo.report_id == rep.id).one()
        assert ph.path.startswith("prive/")
        assert client.get("/api/health").json()["masking"] == "indisponible"
    finally:
        monkeypatch.undo()
        detector._sessions.cache_clear()
    # même vérifié par un modérateur, la photo privée n'est jamais servie au public
    assert client.patch(f"/api/reports/{rep.id}", json={"status": "verified"}).status_code == 200
    assert client.get(f"/api/reports/{rep.id}/photo", headers={"X-Salubri-Token": ""}).status_code == 404
    assert client.get(f"/api/reports/{rep.id}/photo").status_code == 200  # modérateur : oui
    out = backfill(db)
    db.expire_all()
    ph = db.query(Photo).filter(Photo.report_id == rep.id).one()
    assert not ph.path.startswith("prive/") and out["masquees"] >= 1
    assert _textured(_stored(db, rep.id), FACE) < 0.25
    assert client.get(f"/api/reports/{rep.id}/photo", headers={"X-Salubri-Token": ""}).status_code == 200


def test_detector_crash_keeps_photo_private(db, client, world, monkeypatch):  # type: ignore[no-untyped-def]
    from salubri_api.services import masking

    def boom(_img):  # type: ignore[no-untyped-def]
        raise RuntimeError("onnxruntime: erreur simulée")

    monkeypatch.setattr(masking, "detect", boom)
    lon, lat = free_point(world, n=74)
    rid = client.post(
        "/api/reports",
        data={"lon": str(lon), "lat": str(lat), "device_id": "m-5"},
        files={"photo": ("p.jpg", PHOTO, "image/jpeg")},
    ).json()["id"]
    rep = db.get(Report, rid)
    assert rep.masking["server"] is None and "détection en échec" in rep.masking["erreur_serveur"]
    assert rep.status == "to_review"
    assert db.query(Photo).filter(Photo.report_id == rep.id).one().path.startswith("prive/")


def test_manual_only_mode_goes_to_moderation(db, client, world):  # type: ignore[no-untyped-def]
    lon, lat = free_point(world, n=75)
    rid = client.post(
        "/api/reports",
        data={
            "lon": str(lon),
            "lat": str(lat),
            "device_id": "m-6",
            "masking_client": json.dumps({"faces": 0, "plates": 0, "manual": 0, "mode": "manuel"}),
        },
        files={"photo": ("p.jpg", PHOTO, "image/jpeg")},
    ).json()["id"]
    rep = db.get(Report, rid)
    assert rep.masking["mode"] == "manuel" and rep.masking["server"] == 2  # le serveur masque quand même
    assert rep.status == "to_review"
    assert any(h["rule"] == "M0" and "à la main" in h["detail"] for h in rep.rule_hits)


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
