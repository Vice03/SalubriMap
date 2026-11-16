# SPDX-License-Identifier: AGPL-3.0-or-later
"""Salubri Go : première visite, puis hors ligne (rechargement + signalement), puis envoi au retour du réseau."""

import io

from PIL import Image


def _photo() -> bytes:
    buf = io.BytesIO()
    Image.effect_noise((640, 480), 80).convert("RGB").save(buf, "JPEG")
    return buf.getvalue()


def test_offline_from_first_visit_then_sync(browser, base):  # type: ignore[no-untyped-def]
    ctx = browser.new_context(
        viewport={"width": 390, "height": 844},
        geolocation={"latitude": 12.3714, "longitude": -1.5197, "accuracy": 12},
        permissions=["geolocation"],
        locale="fr-FR",
    )
    page = ctx.new_page()
    page.goto(f"{base}/go/")
    page.wait_for_selector("text=Prendre une photo")
    page.evaluate("navigator.serviceWorker.ready.then(() => true)")
    page.wait_for_function("navigator.serviceWorker.controller !== null", timeout=15000)

    ctx.set_offline(True)
    page.reload()
    page.wait_for_selector("text=Prendre une photo", timeout=5000)  # l'appli s'ouvre sans réseau

    page.set_input_files("input[type=file]", files=[{"name": "d.jpg", "mimeType": "image/jpeg", "buffer": _photo()}])
    page.locator("button.tile").first.click()
    page.wait_for_selector("text=Précis")
    page.locator("button.btn.primary.big").click()
    page.wait_for_selector("text=Merci")
    page.locator("text=Voir mes signalements").click()
    page.wait_for_selector("text=En attente")
    assert page.locator("nav i").inner_text() == "1"

    ctx.set_offline(False)
    page.evaluate("window.dispatchEvent(new Event('online'))")
    page.wait_for_selector("text=Tout est envoyé", timeout=20000)
    assert page.locator("nav i").count() == 0
    assert "/100" in page.inner_text("main")  # le verdict des règles est affiché
    ctx.close()
