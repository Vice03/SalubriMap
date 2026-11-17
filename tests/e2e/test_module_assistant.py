# SPDX-License-Identifier: AGPL-3.0-or-later
"""Module « Assistant » dans Salubri Map : bouton pour un compte connecté si le module est allumé, absent sinon,
et jamais pour un visiteur."""

import httpx


def _on(base: str) -> bool:
    return bool(httpx.get(f"{base}/api/health", timeout=10).json().get("modules", {}).get("assistant"))


def test_assistant_button_follows_flag_and_role(browser, base):  # type: ignore[no-untyped-def]
    page = browser.new_context(viewport={"width": 1440, "height": 860}, locale="fr-FR").new_page()
    page.goto(f"{base}/journal")
    page.wait_for_timeout(1500)
    assert page.get_by_test_id("assistant-open").count() == 0  # visiteur : jamais
    page.locator(".topbar button:has-text('Se connecter')").click()
    page.fill("input[autocomplete=username]", "demo")
    page.fill("input[autocomplete=current-password]", "ouaga2026")
    page.locator("form button[type=submit]").click()
    page.wait_for_selector("select[aria-label=\"Filtrer par type d'action\"]")
    page.wait_for_timeout(1000)
    if _on(base):
        page.get_by_test_id("assistant-open").click()
        page.get_by_test_id("assistant-panel").wait_for(timeout=5000)
        assert "lecture seule" in page.get_by_test_id("assistant-panel").inner_text()
    else:
        assert page.get_by_test_id("assistant-open").count() == 0
    page.close()
