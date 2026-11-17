# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lot masquage : Salubri Go floute visages et plaques AVANT la file d'attente, hors ligne, avec retouche manuelle."""

from pathlib import Path

PHOTO = (Path(__file__).parent / "fixtures" / "visage_et_plaque.jpg").read_bytes()
SMALL = (Path(__file__).parent / "fixtures" / "petit_visage.jpg").read_bytes()
FACE = (181, 67, 88, 107)  # x, y, w, h dans l'image (référence Python)
PLATE = (842, 197, 182, 69)

# Détail d'une zone : part des pixels où le laplacien de la luminance dépasse 12. Élevée sur un vrai visage ou une
# plaque ; faible sur des aplats pixellisés, où seuls les bords des cases (une ligne sur ~20) restent texturés.
DETAIL_JS = """async ([blob, x, y, w, h]) => {
  const b = await createImageBitmap(blob)
  const c = document.createElement('canvas'); c.width = b.width; c.height = b.height
  const g = c.getContext('2d'); g.drawImage(b, 0, 0)
  const d = g.getImageData(x, y, w, h).data
  const L = (i) => 0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2]
  let busy = 0, n = 0
  for (let yy = 1; yy < h - 1; yy++) for (let xx = 1; xx < w - 1; xx++) {
    const i = yy * w + xx
    if (Math.abs(4 * L(i) - L(i - 1) - L(i + 1) - L(i - w) - L(i + w)) > 12) busy++
    n++
  }
  return { detail: busy / n, width: b.width }  // part des pixels « texturés »
}"""

OUTBOX_JS = """() => new Promise((res, rej) => {
  const r = indexedDB.open('salubri-go')
  r.onsuccess = () => { const q = r.result.transaction('outbox').objectStore('outbox').getAll(); q.onsuccess = () => res(q.result); q.onerror = rej }
  r.onerror = rej
})"""


def _ctx(browser):  # type: ignore[no-untyped-def]
    ctx = browser.new_context(
        viewport={"width": 390, "height": 844},
        geolocation={"latitude": 12.3714, "longitude": -1.5197, "accuracy": 12},
        permissions=["geolocation"],
        locale="fr-FR",
    )
    return ctx, ctx.new_page()


def test_masked_preview_then_masked_photo_queued_offline(browser, base):  # type: ignore[no-untyped-def]
    ctx, page = _ctx(browser)
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{base}/go/")
    page.wait_for_selector("text=Prendre une photo")
    page.wait_for_timeout(1500)  # service worker installé : modèles et moteur en cache
    ctx.set_offline(True)  # tout ce qui suit se passe sans réseau
    page.set_input_files("input[type=file]", files=[{"name": "rue.jpg", "mimeType": "image/jpeg", "buffer": PHOTO}])
    page.wait_for_selector("text=floutés automatiquement", timeout=60000)
    status = page.inner_text(".mask-status")
    assert "1 visage(s) et 1 plaque(s)" in status, status
    assert page.locator(".mask-box").count() == 2
    page.locator("button.tile").first.click()
    page.locator(".sticky-send button").click()
    page.wait_for_selector("text=Merci")
    items = page.evaluate(OUTBOX_JS)
    assert len(items) == 1 and items[0]["state"] == "pending" and items[0]["masking"] == {"faces": 1, "plates": 1, "manual": 0, "mode": "auto"}
    # la photo en file d'attente est la photo masquée : le visage et la plaque ne sont plus que des aplats
    face = page.evaluate(f"async () => {{ const it = (await ({OUTBOX_JS})())[0]; return ({DETAIL_JS})([it.photo, {', '.join(map(str, FACE))}]) }}")
    plate = page.evaluate(f"async () => {{ const it = (await ({OUTBOX_JS})())[0]; return ({DETAIL_JS})([it.photo, {', '.join(map(str, PLATE))}]) }}")
    assert face["width"] == 1309
    # contrôle de la mesure : les mêmes zones dans la photo d'origine
    raw = page.evaluate(
        f"async (bytes) => ({DETAIL_JS})([new Blob([new Uint8Array(bytes)], {{type: 'image/jpeg'}}), {', '.join(map(str, FACE))}])",
        list(PHOTO),
    )
    raw_plate = page.evaluate(
        f"async (bytes) => ({DETAIL_JS})([new Blob([new Uint8Array(bytes)], {{type: 'image/jpeg'}}), {', '.join(map(str, PLATE))}])",
        list(PHOTO),
    )
    print("détail visage", raw["detail"], "→", face["detail"], "; plaque", raw_plate["detail"], "→", plate["detail"])
    assert face["detail"] < 0.4 * raw["detail"], (face, raw)
    assert plate["detail"] < 0.4 * raw_plate["detail"], (plate, raw_plate)
    ctx.set_offline(False)
    page.evaluate("window.dispatchEvent(new Event('online'))")
    page.locator("text=Voir mes signalements").click()
    page.wait_for_selector("text=Tout est envoyé", timeout=30000)
    assert not errors, errors
    ctx.close()


def test_false_positive_undo_and_manual_zone(browser, base):  # type: ignore[no-untyped-def]
    ctx, page = _ctx(browser)
    page.goto(f"{base}/go/")
    page.set_input_files("input[type=file]", files=[{"name": "rue.jpg", "mimeType": "image/jpeg", "buffer": PHOTO}])
    page.wait_for_selector("text=floutés automatiquement", timeout=60000)
    # toucher le cadre de la plaque l'annule
    page.locator(".mask-box[aria-label^='plaque']").click()
    page.wait_for_selector("text=1 visage(s) et 0 plaque(s)")
    # tracer une zone à la main
    page.locator("button:has-text('Flouter une zone')").click()
    area = page.locator(".mask-area").bounding_box()
    page.mouse.move(area["x"] + area["width"] * 0.80, area["y"] + area["height"] * 0.10)
    page.mouse.down()
    page.mouse.move(area["x"] + area["width"] * 0.95, area["y"] + area["height"] * 0.30, steps=5)
    page.mouse.up()
    page.wait_for_selector(".mask-box[aria-label^='manuel']")
    page.wait_for_selector("text=Retirer la dernière zone")
    assert page.locator(".mask-box").count() == 3
    ctx.close()


def test_manual_only_mode_requires_explicit_confirmation(browser, base):  # type: ignore[no-untyped-def]
    """Lot 2.2 : modèles impossibles à charger → rien ne part sans zone tracée ou « Aucune personne ni plaque »."""
    ctx, page = _ctx(browser)
    ctx.route("**/go/models/**", lambda route: route.abort())  # détecteurs indisponibles sur ce « téléphone »
    page.goto(f"{base}/go/")
    page.wait_for_selector("text=Prendre une photo")
    page.set_input_files("input[type=file]", files=[{"name": "rue.jpg", "mimeType": "image/jpeg", "buffer": PHOTO}])
    page.wait_for_selector("text=Détection automatique indisponible", timeout=60000)
    page.locator("button.tile").first.click()
    send = page.locator(".sticky-send button")
    page.wait_for_timeout(500)
    assert send.is_disabled()
    assert "Aucune personne ni plaque visible" in page.inner_text("body")
    page.locator(".mask-confirm input").check()
    for _ in range(50):
        if send.is_enabled():
            break
        page.wait_for_timeout(100)
    assert send.is_enabled()
    ctx.set_offline(True)
    send.click()
    page.wait_for_selector("text=Merci")
    items = page.evaluate(OUTBOX_JS)
    assert items[-1]["masking"]["mode"] == "manuel"
    ctx.close()


def test_small_background_face_found_by_tiles(browser, base):  # type: ignore[no-untyped-def]
    """Lot 2.1 : un visage de 46 px sur une photo de 2400 px n'est vu que par les tuiles (pas par l'image entière)."""
    ctx, page = _ctx(browser)
    page.goto(f"{base}/go/")
    page.wait_for_selector("text=Prendre une photo")
    page.set_input_files("input[type=file]", files=[{"name": "loin.jpg", "mimeType": "image/jpeg", "buffer": SMALL}])
    page.wait_for_selector(".mask-status:has-text('visage(s)'), .mask-status:has-text('Aucun visage')", timeout=60000)
    status = page.inner_text(".mask-status")
    assert "1 visage(s)" in status, status
    ms = int(page.get_attribute(".mask-status", "data-ms") or 0)
    print("temps de détection (photo 2400 px)", ms, "ms")
    ctx.close()
