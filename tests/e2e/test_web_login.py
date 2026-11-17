# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lot A7 : panneau de connexion, barre du haut, boutons réservés, jeton jamais dans l'URL ni localStorage."""


def test_login_panel_roles_and_sign_out(browser, base):  # type: ignore[no-untyped-def]
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="fr-FR")
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: errors.append(f"fenêtre native : {d.message}"))  # plus de window.prompt
    page.goto(f"{base}/signalements")
    page.wait_for_selector("text=Vue publique")

    # visiteur : Importer désactivé avec la raison
    imp = page.locator("button:has-text('Importer')")
    assert imp.is_disabled()
    assert "administrateur" in (imp.get_attribute("title") or "")

    # connexion ratée puis réussie
    page.locator(".topbar button:has-text('Se connecter')").click()
    page.fill("input[autocomplete=username]", "demo")
    page.fill("input[autocomplete=current-password]", "mauvais-mdp")
    page.locator("form button[type=submit]").click()
    page.wait_for_selector("text=Identifiant ou mot de passe incorrect")
    page.fill("input[autocomplete=current-password]", "ouaga2026")
    page.locator("form button[type=submit]").click()
    page.wait_for_selector(".user-chip .role-pill")
    assert page.locator(".role-pill").inner_text() == "administrateur"
    assert not imp.is_disabled()
    page.wait_for_selector("text=Vue publique", state="detached")  # la mairie voit tout

    # le jeton : sessionStorage seulement, jamais dans l'URL ni dans localStorage
    store = page.evaluate("[sessionStorage.getItem('salubri_session'), JSON.stringify(localStorage)]")
    assert store[0] and "token" in store[0]
    assert "token" not in store[1] and "ouaga2026" not in store[1]
    assert "token" not in page.url

    # modération possible depuis la fiche
    page.locator("table tbody tr").first.click()
    assert not page.locator("button:has-text('Vérifier')").is_disabled()
    page.keyboard.press("Escape")

    # déconnexion : retour à la vue publique, boutons de nouveau désactivés
    page.locator("button[aria-label='Se déconnecter']").click()
    page.wait_for_selector("text=Vue publique")
    assert imp.is_disabled()
    assert page.evaluate("sessionStorage.getItem('salubri_session')") is None
    assert not errors, errors
    ctx.close()


def test_write_refused_opens_login_panel_instead_of_prompt(browser, base):  # type: ignore[no-untyped-def]
    """Session révoquée entre deux clics : l'écriture refusée (401) ouvre le panneau, jamais window.prompt."""
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="fr-FR")
    page = ctx.new_page()
    dialogs: list[str] = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    page.goto(f"{base}/scenario")
    page.locator(".topbar button:has-text('Se connecter')").click()
    page.fill("input[autocomplete=username]", "demo")
    page.fill("input[autocomplete=current-password]", "ouaga2026")
    page.locator("form button[type=submit]").click()
    page.wait_for_selector(".user-chip .role-pill")
    page.route(
        "**/api/scenarios/*",
        lambda r: r.fulfill(status=401, json={"detail": "Session expirée, reconnectez-vous"})
        if r.request.method == "PATCH"
        else r.continue_(),
    )
    seasons = page.locator("button:has-text('Saison des pluies'), button:has-text('Saison sèche')")
    target = seasons.nth(1) if "on" in (seasons.nth(0).get_attribute("class") or "") else seasons.nth(0)
    target.click()
    page.wait_for_selector("text=Connexion mairie")
    assert not dialogs
    ctx.close()
