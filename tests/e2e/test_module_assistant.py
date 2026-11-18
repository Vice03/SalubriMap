# SPDX-License-Identifier: AGPL-3.0-or-later
"""Module « Assistant » dans Salubri Map : bulle visible de tous si le module est allumé (le visiteur est invité à se
connecter et ne peut rien demander), absente sinon."""

import httpx


def _on(base: str) -> bool:
    return bool(httpx.get(f"{base}/api/health", timeout=10).json().get("modules", {}).get("assistant"))


def test_assistant_button_follows_flag_and_role(browser, base):  # type: ignore[no-untyped-def]
    page = browser.new_context(viewport={"width": 1440, "height": 860}, locale="fr-FR").new_page()
    page.goto(f"{base}/journal")
    page.wait_for_timeout(1500)
    if _on(base):  # visiteur : il voit la bulle mais ne peut pas poser de question
        page.get_by_test_id("assistant-open").click()
        panel = page.get_by_test_id("assistant-panel")
        panel.wait_for(timeout=5000)
        assert "demo / ouaga2026" in panel.inner_text()
        assert page.locator("[aria-label=\"Question à l'assistant\"]").is_disabled()
        panel.locator("button[aria-label=Fermer]").click()
    else:
        assert page.get_by_test_id("assistant-open").count() == 0
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
