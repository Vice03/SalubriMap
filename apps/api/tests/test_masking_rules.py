# SPDX-License-Identifier: AGPL-3.0-or-later
"""Masquage, étape 4 : les règles anti-pièges fonctionnent toujours sur des photos masquées.

R2 (photo réutilisée) compare l'empreinte et le pHash de la photo REÇUE (masquée sur le téléphone) ;
R11 (photo peu informative) mesure la variance de luminance ; taille et dimensions ne changent pas.
Aucun seuil n'a été modifié : ces tests montrent que ce n'était pas nécessaire.
"""

import io
from pathlib import Path

import numpy as np
import pytest
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


@pytest.mark.parametrize("frac", [0.1, 0.3, 0.6])
def test_heavy_masking_keeps_r11_and_r12_quiet(frac: float) -> None:
    """Lot 2.4 : même si le masquage couvre 60 % de la photo (foule), R11 (variance de luminance) et R12 (photo
    trop légère pour un volume « camion ») ne se déclenchent pas sur une photo normale. Mesures sur la fixture
    (136 Ko) : 117 Ko / 90 Ko / 62 Ko pour 10 / 30 / 60 % masqués, seuil R12 50 Ko ; variance ≥ 2 900, seuil 25.
    Aucun seuil changé ; une photo déjà proche de 50 Ko et masquée aux deux tiers peut passer dessous (R12 n'enlève
    alors que 10 points, indicatif)."""
    im = Image.open(io.BytesIO(PHOTO)).convert("RGB")
    arr = np.array(im)
    w, h = im.size
    pixelate(arr, [Box(0, 0, w * frac**0.5, h * frac**0.5, "visage", 1)], margin=0)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, "JPEG", quality=88)
    info, th = analyze(buf.getvalue()), ValidationThresholds()
    assert info.luminance_var >= th.luminance_var_min
    assert info.bytes >= th.truck_photo_min_bytes
    assert info.bytes >= (1 - frac) * len(PHOTO) * 0.75  # la taille baisse à peu près comme la part masquée
