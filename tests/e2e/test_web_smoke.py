# SPDX-License-Identifier: AGPL-3.0-or-later
"""Salubri Map/Sim : chaque page s'affiche sans erreur JavaScript, sur ordinateur et en largeur téléphone."""

import pytest

PAGES = {
    "/": "Dépotoirs actifs",
    "/carte": "Points de regroupement",
    "/signalements": "Signalements",
    "/scenario": "Saison sèche",
    "/comparer": "Comparer deux scénarios",
    "/journal": "Journal des actions",
}


@pytest.mark.parametrize("width", [1440, 820, 390])
def test_pages_render_without_js_errors(browser, base, width):  # type: ignore[no-untyped-def]
    page = browser.new_context(viewport={"width": width, "height": 860}, locale="fr-FR").new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    for path, text in PAGES.items():
        page.goto(f"{base}{path}")
        page.wait_for_selector(f"text={text}", timeout=15000)
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert overflow <= 2, f"{path} déborde de {overflow}px en largeur {width}"
    assert not errors, errors
    page.close()


def test_dashboard_first_paint_does_not_load_maplibre_eagerly(browser, base):  # type: ignore[no-untyped-def]
    """Lot E : MapLibre n'est pas dans le HTML initial (chargé à l'affichage de la carte seulement)."""
    page = browser.new_context(viewport={"width": 1440, "height": 860}).new_page()
    html = page.request.get(f"{base}/").text()
    assert "maplibre" not in html
    page.close()


def test_journal_sentences_and_filters(browser, base):  # type: ignore[no-untyped-def]
    page = browser.new_context(viewport={"width": 1440, "height": 860}, locale="fr-FR").new_page()
    page.goto(f"{base}/journal")
    page.locator(".topbar button:has-text('Se connecter')").click()
    page.fill("input[autocomplete=username]", "demo")
    page.fill("input[autocomplete=current-password]", "ouaga2026")
    page.locator("form button[type=submit]").click()
    page.wait_for_selector("select[aria-label=\"Filtrer par type d'action\"]")
    body = page.inner_text("table")
    assert "{" not in body  # plus de JSON brut dans le journal
    page.select_option("select[aria-label=\"Filtrer par type d'action\"]", index=1)
    assert page.locator("table tbody tr").count() >= 1
    page.close()
