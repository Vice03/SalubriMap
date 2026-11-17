# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lot A3 : force brute sur la connexion et pourriel de signalements."""

from tests.conftest import free_point, post_report
from tests.test_accounts import make_user

from salubri_api.services.ratelimit import LOGIN_MAX_FAILURES, SlidingWindow


def _login(client, login: str, password: str, ip: str = "10.0.0.1"):  # type: ignore[no-untyped-def]
    return client.post(
        "/api/auth/login",
        json={"login": login, "password": password},
        headers={"X-Salubri-Token": "", "X-Real-IP": ip},
    )


def test_login_locked_after_five_failures_then_429_in_french(db, client):  # type: ignore[no-untyped-def]
    make_user(db, "awa", "moderateur")
    for _ in range(LOGIN_MAX_FAILURES):
        assert _login(client, "awa", "mauvais-mdp").status_code == 401
    r = _login(client, "awa", "motdepasse-123")  # même le bon mot de passe est refusé pendant le blocage
    assert r.status_code == 429
    assert "Trop de tentatives" in r.json()["detail"] and "min" in r.json()["detail"]
    assert 0 < int(r.headers["Retry-After"]) <= 15 * 60
    # depuis une autre adresse, le compte reste bloqué (clé par identifiant)
    assert _login(client, "AWA ", "motdepasse-123", ip="10.0.0.9").status_code == 429


def test_login_blocked_per_ip_across_logins(db, client):  # type: ignore[no-untyped-def]
    make_user(db, "bila", "admin")
    for i in range(LOGIN_MAX_FAILURES):
        assert _login(client, f"essai{i}", "mauvais-mdp", ip="10.0.0.2").status_code == 401
    assert _login(client, "bila", "motdepasse-123", ip="10.0.0.2").status_code == 429
    assert _login(client, "bila", "motdepasse-123", ip="10.0.0.3").status_code == 200


def test_success_resets_login_counter(db, client):  # type: ignore[no-untyped-def]
    make_user(db, "chef", "admin")
    for _ in range(LOGIN_MAX_FAILURES - 1):
        _login(client, "chef", "mauvais-mdp", ip="10.0.1.1")
    assert _login(client, "chef", "motdepasse-123", ip="10.0.1.2").status_code == 200
    for _ in range(LOGIN_MAX_FAILURES - 1):
        _login(client, "chef", "mauvais-mdp", ip="10.0.1.3")
    assert _login(client, "chef", "motdepasse-123", ip="10.0.1.4").status_code == 200


def test_sliding_window_expires() -> None:
    w = SlidingWindow(60)
    for t in (0.0, 10.0, 20.0):
        w.add("k", now=t)
    assert w.count("k", now=30.0) == 3
    assert w.retry_after("k", now=30.0) == 31
    assert w.count("k", now=65.0) == 2
    assert w.count("k", now=200.0) == 0


def test_device_over_hourly_cap_gets_429_and_resend_stays_idempotent(db, client, world):  # type: ignore[no-untyped-def]
    from salubri_api.models import Commune

    c = db.query(Commune).one()
    v = dict(c.params_default)
    v["validation"] = {**v["validation"], "spam_per_hour": 2, "spam_block_factor": 2}  # plafond = 4 / h
    c.params_default = v
    db.commit()
    first = None
    for i in range(4):
        out = post_report(client, free_point(world, n=i), device_id="tel-spam", client_id=f"c-{i}")
        first = first or out
    data = {"lon": "-1.54", "lat": "12.35", "device_id": "tel-spam", "client_id": "c-99"}
    r = client.post("/api/reports", data=data)
    assert r.status_code == 429
    assert "Trop de signalements" in r.json()["detail"]
    # un renvoi d'un signalement déjà reçu (file d'attente du téléphone) répond toujours 200
    again = client.post(
        "/api/reports", data={"lon": "-1.54", "lat": "12.35", "device_id": "tel-spam", "client_id": "c-0"}
    )
    assert again.status_code == 200 and again.json()["id"] == first["id"]
    # un autre téléphone n'est pas concerné
    assert post_report(client, free_point(world, n=9), device_id="tel-autre")["id"]
