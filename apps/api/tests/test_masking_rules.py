# SPDX-License-Identifier: AGPL-3.0-or-later
"""Masquage, étape 4 : les règles anti-pièges fonctionnent toujours sur des photos masquées.

R2 (photo réutilisée) compare l'empreinte et le pHash de la photo REÇUE (masquée sur le téléphone) ;
R11 (photo peu informative) mesure la variance de luminance ; taille et dimensions ne changent pas.
Aucun seuil n'a été modifié : ces tests montrent que ce n'était pas nécessaire.
"""

import io
from pathlib import Path

import numpy as np
from PIL import Image

from conftest import free_point
from salubri_api.models import Report
from salubri_api.services.masking.detector import Box, pixelate
from salubri_api.services.params import ValidationThresholds
from salubri_api.services.validation.photo import analyze, hamming

PHOTO = (Path(__file__).parent / "fixtures" / "visage_et_plaque.jpg").read_bytes()
FACE, PLATE = (181, 67, 88, 107), (842, 197, 182, 69)


def masked(quality: int = 88) -> bytes:
    arr = np.array(Image.open(io.BytesIO(PHOTO)).convert("RGB"))
    pixelate(arr, [Box(*FACE, "visage", 1), Box(*PLATE, "plaque", 1)])
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, "JPEG", quality=quality)
    return buf.getvalue()


def test_masking_keeps_phash_close_luminance_and_size() -> None:
    a, b = analyze(PHOTO), analyze(masked())
    th = ValidationThresholds()
    d = hamming(a.phash, b.phash)
    print("écart pHash original / masqué :", d, "/ 64")
    assert d <= th.phash_max_hamming  # la même scène, masquée ou non, reste « quasi identique » pour R2
    assert b.luminance_var >= th.luminance_var_min  # R11 ne prend pas une photo masquée pour une photo vide
    assert (b.width, b.height) == (a.width, a.height)


def _send(client, world, n: int, photo: bytes, device: str):  # type: ignore[no-untyped-def]
    lon, lat = free_point(world, n=n)
    r = client.post(
        "/api/reports",
        data={"lon": str(lon), "lat": str(lat), "device_id": device},
        files={"photo": ("p.jpg", photo, "image/jpeg")},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _rules(db, rid) -> set[str]:  # type: ignore[no-untyped-def]
    return {h["rule"] for h in db.get(Report, rid).rule_hits}


def test_same_masked_photo_from_two_phones_is_caught(db, client, world):  # type: ignore[no-untyped-def]
    m = masked()
    _send(client, world, 80, m, "tel-a")
    second = _send(client, world, 81, m, "tel-b")
    assert "R2" in _rules(db, second["id"])


def test_masked_copy_of_an_unmasked_photo_is_caught(db, client, world):  # type: ignore[no-untyped-def]
    _send(client, world, 82, PHOTO, "ancienne-app")  # photo en clair (ancienne version, masquée par le serveur)
    second = _send(client, world, 83, masked(70), "nouvelle-app")  # la même, masquée sur un autre téléphone
    assert "R2" in _rules(db, second["id"])


def test_masked_photo_is_not_uninformative(db, client, world):  # type: ignore[no-untyped-def]
    out = _send(client, world, 84, masked(), "tel-c")
    assert "R11" not in _rules(db, out["id"])
