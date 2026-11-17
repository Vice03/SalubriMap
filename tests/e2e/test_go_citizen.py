# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lot D : Salubri Go parle au citoyen (pas de score brut), suit son signalement, et refuse le doublon de photo."""

from test_go_offline import _photo


def _send(page, base, photo: bytes):  # type: ignore[no-untyped-def]
    page.goto(f"{base}/go/")
    page.wait_for_selector("text=Prendre une photo")
    page.set_input_files("input[type=file]", files=[{"name": "d.jpg", "mimeType": "image/jpeg", "buffer": photo}])
    page.locator("button.tile").first.click()
    page.wait_for_selector("text=Précis")
    page.locator(".sticky-send button").click()
    page.wait_for_selector("text=Merci")
    page.locator("text=Voir mes signalements").click()
    page.wait_for_selector("text=Tout est envoyé", timeout=20000)
    first = page.locator(".card.item").first
    for _ in range(50):  # (pas de wait_for_function : la CSP interdit l'évaluation de chaînes, c'est voulu)
        if first.locator(".pill").count() and "En attente" not in first.inner_text():
            break
        page.wait_for_timeout(200)
    page.wait_for_timeout(800)  # suivi relu depuis l'API


def _ctx(browser):  # type: ignore[no-untyped-def]
    ctx = browser.new_context(
        viewport={"width": 390, "height": 844},
        geolocation={"latitude": 12.3714, "longitude": -1.5197, "accuracy": 12},
        permissions=["geolocation"],
        locale="fr-FR",
    )
    return ctx, ctx.new_page()


def test_citizen_wording_timeline_and_steps(browser, base):  # type: ignore[no-untyped-def]
    ctx, page = _ctx(browser)
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{base}/go/")
    page.wait_for_selector("text=Prendre une photo")
    # indicateur d'étapes et raison claire du bouton désactivé
    assert page.locator(".steps li").count() == 4
    assert page.locator(".sticky-send button").is_disabled()
    page.wait_for_selector("text=Choisissez le type de déchets")
    # quantités en images, sans m³ affiché
    seg = page.locator(".seg").inner_text()
    assert "m³" not in seg and "Une brouette" in seg
    _send(page, base, _photo())
    card = page.locator(".card.item").first.inner_text()
    assert "/100" not in card and "Rejeté" not in card
    assert any(t in card for t in ("Merci ! La mairie va vérifier", "Signalement confirmé", "Nous n'avons pas pu confirmer"))
    if "Nous n'avons pas pu confirmer" not in card:
        assert page.locator(".timeline li").count() == 4
        assert "done" in (page.locator(".timeline li").first.get_attribute("class") or "")  # « Reçu »
    assert not errors, errors
    ctx.close()


def test_same_photo_twice_is_not_confirmed_and_explains_why(browser, base):  # type: ignore[no-untyped-def]
    ctx, page = _ctx(browser)
    photo = _photo()
    _send(page, base, photo)
    _send(page, base, photo)  # même photo : règle des doublons
    newest = page.locator(".card.item").first
    assert "/100" not in newest.inner_text()
    why = newest.locator("details.why")
    assert why.count() == 1
    why.locator("summary").click()
    assert "photo" in why.inner_text().lower()
    ctx.close()


def test_pwa_manifest_has_png_icons(browser, base):  # type: ignore[no-untyped-def]
    ctx, page = _ctx(browser)
    page.goto(f"{base}/go/manifest.webmanifest")
    import json

    icons = json.loads(page.locator("body").inner_text())["icons"]
    sizes = {(i["sizes"], i.get("purpose")) for i in icons}
    assert ("192x192", "any") in sizes and ("512x512", "any") in sizes and ("512x512", "maskable") in sizes
    for i in icons:
        assert page.request.get(f"{base}{i['src']}").ok
    ctx.close()
