# SPDX-License-Identifier: AGPL-3.0-or-later
"""Module « Saisons » dans Salubri Map et Salubri Go : visible s'il est allumé, absent sinon."""

import httpx
import pytest


def _on(base: str) -> bool:
    return bool(httpx.get(f"{base}/api/health", timeout=10).json().get("modules", {}).get("seasons"))


def test_routes_panel_follows_the_module_flag(browser, base):  # type: ignore[no-untyped-def]
    page = browser.new_context(viewport={"width": 1440, "height": 860}, locale="fr-FR").new_page()
    page.goto(f"{base}/carte")
    page.get_by_test_id("map-licence").wait_for(timeout=15000)
    if _on(base):
        page.get_by_test_id("seasons-panel").wait_for(timeout=15000)
        assert "route(s) impraticable(s)" in page.get_by_test_id("seasons-panel").inner_text()
    else:
        page.wait_for_timeout(1500)
        assert page.get_by_test_id("seasons-panel").count() == 0
    page.close()


def test_go_road_tab_follows_the_module_flag(browser, base):  # type: ignore[no-untyped-def]
    page = browser.new_context(viewport={"width": 390, "height": 800}, locale="fr-FR").new_page()
    page.goto(f"{base}/go/")
    page.get_by_role("button", name="Signaler").wait_for(timeout=15000)
    page.wait_for_timeout(1500)
    tab = page.get_by_role("button", name="Route")
    if not _on(base):
        assert tab.count() == 0
        pytest.skip("module « Saisons » éteint : onglet absent, comme attendu")
    tab.click()
    page.get_by_text("Route impraticable").first.wait_for(timeout=5000)
    page.close()
