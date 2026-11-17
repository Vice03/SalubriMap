# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lot A3 : force brute sur la connexion et pourriel de signalements."""

from tests.conftest import free_point, post_report
from tests.test_accounts import make_user

from salubri_api.services.ratelimit import IP_MAX_FAILURES, LOGIN_MAX_FAILURES, LOGIN_SLOW_AFTER, SlidingWindow


def _login(client, login: str, password: str, ip: str = "10.0.0.1"):  # type: ignore[no-untyped-def]
    return client.post(
        "/api/auth/login",
        json={"login": login, "password": password},
        headers={"X-Salubri-Token": "", "X-Real-IP": ip},
    )


def test_login_locked_per_login_and_address_then_429_in_french(db, client):  # type: ignore[no-untyped-def]
    make_user(db, "awa", "moderateur")
    for _ in range(LOGIN_MAX_FAILURES):
        assert _login(client, "awa", "mauvais-mdp").status_code == 401
    r = _login(client, "awa", "motdepasse-123")  # même le bon mot de passe est refusé depuis cette adresse
    assert r.status_code == 429
    assert "Trop de tentatives" in r.json()["detail"] and "min" in r.json()["detail"]
    assert 0 < int(r.headers["Retry-After"]) <= 15 * 60
    # lot 1.1 : le blocage porte sur la paire (login, adresse) ; le titulaire se connecte d'ailleurs
    assert _login(client, "AWA ", "motdepasse-123", ip="10.0.0.9").status_code == 200


def test_ten_failures_on_demo_do_not_lock_out_the_real_user(db, client):  # type: ignore[no-untyped-def]
    for _ in range(10):  # le compte demo existe en mode démonstration (mot de passe ouaga2026)
        _login(client, "demo", "mauvais-mdp", ip="198.51.100.7")
    assert _login(client, "demo", "ouaga2026", ip="10.0.0.20").status_code == 200


def test_address_blocked_after_twenty_failures_across_logins(db, client):  # type: ignore[no-untyped-def]
    make_user(db, "bila", "admin")
    for i in range(IP_MAX_FAILURES):
        assert _login(client, f"essai{i % 4}", "mauvais-mdp", ip="10.0.0.2").status_code == 401
    assert _login(client, "bila", "motdepasse-123", ip="10.0.0.2").status_code == 429
    assert _login(client, "bila", "motdepasse-123", ip="10.0.0.3").status_code == 200


def test_many_failures_on_one_login_only_slow_down_the_failures(db, client, monkeypatch):  # type: ignore[no-untyped-def]
    from salubri_api.routers import auth

    waits: list[float] = []
    monkeypatch.setattr(auth, "sleep", waits.append)
    make_user(db, "chef2", "admin")
    for i in range(LOGIN_SLOW_AFTER + 4):  # 24 échecs depuis 24 adresses : jamais 5 par paire
        assert _login(client, "chef2", "mauvais-mdp", ip=f"10.9.0.{i}").status_code == 401
    assert waits == [1.0, 2.0, 4.0, 8.0]
    waits.clear()
    assert _login(client, "chef2", "motdepasse-123", ip="10.9.1.1").status_code == 200  # tout de suite
    assert waits == []
    _login(client, "chef2", "mauvais-mdp", ip="10.9.0.99")
    assert waits == [8.0]  # plafonné


def test_unlock_command_lifts_the_lock(db, client):  # type: ignore[no-untyped-def]
    from salubri_api.users import main

    make_user(db, "dao", "moderateur")
    for _ in range(LOGIN_MAX_FAILURES):
        _login(client, "dao", "mauvais-mdp")
    assert _login(client, "dao", "motdepasse-123").status_code == 429
    assert main(["unlock", "dao"]) == 0
    assert _login(client, "dao", "motdepasse-123").status_code == 200


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
