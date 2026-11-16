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


@pytest.mark.parametrize("width", [1440, 390])
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
