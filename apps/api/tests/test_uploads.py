# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lot A5 : photos vérifiées par leur contenu, réencodées, noms aléatoires ; archives ZIP bornées."""

import io
import json
import re
import zipfile

import pytest
from PIL import Image

from conftest import free_point, jpeg, post_report
from salubri_api.config import get_settings
from salubri_api.models import Photo
from salubri_api.seed.synthetic import photo_for_name
from salubri_api.services.importers.run import ZIP_MAX_ENTRIES, detect_and_parse
from salubri_api.services.validation.photo import STORED_MAX_SIDE, analyze


def _img(fmt: str, size=(300, 200)) -> bytes:  # type: ignore[no-untyped-def]
    buf = io.BytesIO()
    Image.new("RGB", size, (140, 90, 50)).save(buf, fmt)
    return buf.getvalue()


def _send(client, world, photo: bytes, n: int, name: str = "p.jpg"):  # type: ignore[no-untyped-def]
    lon, lat = free_point(world, n=n)
    return client.post(
        "/api/reports",
        data={"lon": str(lon), "lat": str(lat), "device_id": f"u-{n}", "client_id": f"u-{n}"},
        files={"photo": (name, photo, "image/jpeg")},
    )


@pytest.mark.parametrize(
    ("payload", "why"),
    [
        (b"<?php echo 'pas une image'; ?>", "illisible"),
        (b"\xff\xd8\xff\xe0" + b"\x00" * 500, "illisible"),  # en-tête JPEG, corps vide
        (_img("GIF"), "Format de photo refusé"),
        (_img("BMP"), "Format de photo refusé"),
    ],
)
def test_fake_or_unsupported_images_are_422(db, client, world, payload, why):  # type: ignore[no-untyped-def]
    r = _send(client, world, payload, n=1, name="vraie-photo.jpg")  # l'extension ne compte pas
    assert r.status_code == 422 and why in r.text


def test_pixel_bomb_is_rejected_without_decoding() -> None:
    bomb = _img("PNG", size=(8000, 6000))  # 48 Mpx d'une seule couleur : quelques dizaines de Ko
    assert len(bomb) < 1_000_000
    with pytest.raises(ValueError, match="trop grande"):
        analyze(bomb)


def test_png_and_webp_accepted_and_stored_as_clean_jpeg(db, client, world):  # type: ignore[no-untyped-def]
    for n, fmt in ((2, "PNG"), (3, "WEBP")):
        assert _send(client, world, _img(fmt), n=n, name="x.png").status_code == 201
    for ph in db.query(Photo).all():
        assert re.fullmatch(r"[0-9a-f]{32}\.jpg", ph.path)  # nom aléatoire, jamais celui du téléphone
        with Image.open(get_settings().photos_dir / ph.path) as im:
            assert im.format == "JPEG"


def test_stored_copy_has_no_exif_but_rules_keep_gps(db, client, world):  # type: ignore[no-untyped-def]
    raw = photo_for_name("demo-91-exifgps_12.3714_1.5197.jpg")
    assert raw and Image.open(io.BytesIO(raw)).getexif()
    rid = post_report(client, free_point(world, n=4), raw, device_id="u-4")["id"]
    ph = db.query(Photo).filter(Photo.report_id == rid).one()
    assert abs(ph.exif_lat - 12.3714) < 1e-3 and abs(ph.exif_lon - 1.5197) < 1e-3  # en base pour les règles
    stored = (get_settings().photos_dir / ph.path).read_bytes()
    assert not Image.open(io.BytesIO(stored)).getexif()
    assert ph.sha256 not in ph.path  # le nom ne révèle pas l'empreinte


def test_big_photo_is_downscaled(db, client, world):  # type: ignore[no-untyped-def]
    rid = post_report(client, free_point(world, n=5), jpeg(5, size=(4000, 3000)), device_id="u-5")["id"]
    ph = db.query(Photo).filter(Photo.report_id == rid).one()
    with Image.open(get_settings().photos_dir / ph.path) as im:
        assert max(im.size) == STORED_MAX_SIDE
    assert (ph.width, ph.height) == (4000, 3000)  # les règles voient les dimensions d'origine


def _zip(entries: dict[str, bytes], compression: int = zipfile.ZIP_DEFLATED) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression) as z:
        for k, v in entries.items():
            z.writestr(k, v)
    return buf.getvalue()


FC = json.dumps({"type": "FeatureCollection", "features": []}).encode()


@pytest.mark.parametrize(
    ("entries", "why"),
    [
        ({"../../etc/evil.geojson": FC}, "chemin interdit"),
        ({"/abs/x.geojson": FC}, "chemin interdit"),
        ({"x.geojson": FC, "bombe.jpg": b"\0" * (60 * 1024 * 1024)}, "dépasse"),
        ({"x.geojson": FC, "bombe.jpg": b"\0" * (20 * 1024 * 1024)}, "bombe"),
    ],
)
def test_dangerous_zips_are_refused(entries, why):  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match=why):
        detect_and_parse("jury.zip", _zip(entries))


def test_zip_with_too_many_entries() -> None:
    entries = {f"p/{i}.txt": b"x" for i in range(ZIP_MAX_ENTRIES + 1)} | {"x.geojson": FC}
    with pytest.raises(ValueError, match="plus de"):
        detect_and_parse("jury.zip", _zip(entries, zipfile.ZIP_STORED))


def test_lying_zip_header_is_refused() -> None:
    data = bytearray(_zip({"x.geojson": FC}, zipfile.ZIP_STORED))
    # réduit la taille annoncée dans le répertoire central : le contenu réel est plus long
    i = data.rfind(b"PK\x01\x02")
    data[i + 24 : i + 28] = (5).to_bytes(4, "little")
    with pytest.raises(ValueError, match="Archive"):
        detect_and_parse("jury.zip", bytes(data))


def test_not_a_zip_and_import_size_cap(client):  # type: ignore[no-untyped-def]
    r = client.post("/api/imports", files={"file": ("jury.zip", b"PK\x03\x04 pas une archive")})
    assert r.status_code == 422 and "ZIP" in r.text


def test_exif_sent_beside_a_masked_photo_feeds_the_rules(db, client, world):  # type: ignore[no-untyped-def]
    """Lot masquage : la photo floutée sur le téléphone n'a plus d'EXIF ; position et date arrivent à part."""
    lon, lat = free_point(world, n=8)
    r = client.post(
        "/api/reports",
        data={
            "lon": str(lon),
            "lat": str(lat),
            "device_id": "u-8",
            "client_id": "u-8",
            "exif_lat": "12.3714",
            "exif_lon": "1.5197",
            "exif_taken_at": "2026-11-17T08:00:00",
        },
        files={"photo": ("p.jpg", _img("JPEG"), "image/jpeg")},
    )
    assert r.status_code == 201, r.text
    ph = db.query(Photo).filter(Photo.report_id == r.json()["id"]).one()
    assert abs(ph.exif_lat - 12.3714) < 1e-6 and abs(ph.exif_lon - 1.5197) < 1e-6
    assert ph.exif_taken_at.isoformat().startswith("2026-11-17T08:00")


def test_exif_in_the_file_wins_over_sent_values(db, client, world):  # type: ignore[no-untyped-def]
    raw = photo_for_name("demo-92-exifgps_12.3714_1.5197.jpg")
    lon, lat = free_point(world, n=9)
    r = client.post(
        "/api/reports",
        data={"lon": str(lon), "lat": str(lat), "device_id": "u-9", "exif_lat": "10.0", "exif_lon": "2.0"},
        files={"photo": ("p.jpg", raw, "image/jpeg")},
    )
    ph = db.query(Photo).filter(Photo.report_id == r.json()["id"]).one()
    assert abs(ph.exif_lat - 12.3714) < 1e-3
