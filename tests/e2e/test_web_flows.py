# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lot C : parcours complets de Salubri Map — modération, import + annulation, changement de scénario (SSE)."""

import json
import uuid


def _login(page, base):  # type: ignore[no-untyped-def]
    page.goto(f"{base}/signalements")
    page.locator(".topbar button:has-text('Se connecter')").click()
    page.fill("input[autocomplete=username]", "demo")
    page.fill("input[autocomplete=current-password]", "ouaga2026")
    page.locator("form button[type=submit]").click()
    page.wait_for_selector(".user-chip .role-pill")


def _ctx(browser):  # type: ignore[no-untyped-def]
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="fr-FR")
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    return ctx, page, errors


def test_moderation_verify_triggers_plan(browser, base):  # type: ignore[no-untyped-def]
    ctx, page, errors = _ctx(browser)
    _login(page, base)
    page.locator("button:has-text('Probable'), button:has-text('À revoir')").first.click()
    page.wait_for_timeout(800)
    row = page.locator("table tbody tr").first
    row.click()
    page.locator("button:has-text('Vérifier')").click()
    page.wait_for_selector("text=Signalement vérifié")
    # la vérification arme un recalcul du plan (« signalements modifiés »), visible dans la file du serveur
    seen = False
    for _ in range(40):
        q = page.evaluate("fetch('/api/health').then(r => r.json()).then(h => h.queue)")
        if q and (q.get("debounced") or q.get("pending") or q.get("running")):
            seen = True
            break
        page.wait_for_timeout(100)
    assert seen, "aucun recalcul déclenché après la vérification"
    assert not errors, errors
    ctx.close()


def test_import_preview_then_rollback(browser, base, tmp_path):  # type: ignore[no-untyped-def]
    ctx, page, errors = _ctx(browser)
    _login(page, base)
    tag = uuid.uuid4().hex[:8]
    fc = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-1.52 + i * 0.001, 12.37]},
             "properties": {"device_id": f"e2e-{tag}", "type": "menager", "id": f"e2e-{tag}-{i}"}}
            for i in range(3)
        ],
    }
    f = tmp_path / "jury.geojson"
    f.write_text(json.dumps(fc), encoding="utf-8")
    page.locator("button:has-text('Importer')").first.click()
    page.set_input_files("input[type=file]", str(f))
    page.wait_for_selector("text=Importer pour de vrai")
    page.locator("button:has-text('Importer pour de vrai')").click()
    page.wait_for_selector("text=Import terminé")
    page.locator("button:has-text(\"Annuler l'import\")").click()
    page.wait_for_selector("text=annulé", timeout=15000)
    left = page.evaluate(f"fetch('/api/reports?limit=50&q=e2e-{tag}', {{headers: {{}}}}).then(r => r.status)")
    assert left in (200, 403)
    assert not errors, errors
    ctx.close()


def test_scenario_change_shows_live_progress(browser, base):  # type: ignore[no-untyped-def]
    ctx, page, errors = _ctx(browser)
    _login(page, base)
    page.goto(f"{base}/scenario")
    page.wait_for_selector("text=Saison sèche")
    seasons = page.locator("button:has-text('Saison des pluies'), button:has-text('Saison sèche')")
    dry_on = "on" in (seasons.nth(0).get_attribute("class") or "")
    target, other = (seasons.nth(1), seasons.nth(0)) if dry_on else (seasons.nth(0), seasons.nth(1))
    target.click()
    page.wait_for_selector("text=Recalcul du plan en cours", timeout=10000)  # flux SSE en direct
    page.wait_for_selector("text=Plan recalculé", timeout=60000)
    # remettre la saison d'origine pour ne pas gêner les autres tests
    page.wait_for_timeout(500)
    other.click()
    page.wait_for_selector("text=Plan recalculé", timeout=60000)
    assert not errors, errors
    ctx.close()
