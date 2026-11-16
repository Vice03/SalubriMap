# SPDX-License-Identifier: AGPL-3.0-or-later
"""A1 — comptes et rôles : chaque route d'écriture exige le bon rôle, le journal signe avec l'utilisateur."""

import re
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from salubri_api.models import User
from salubri_api.models.audit import AuditLog
from salubri_api.services.auth import hash_password, issue_token

# Rôle exigé par chaque route d'écriture. Une route ajoutée sans être classée ici fait échouer le test.
MODERATION = {
    "PATCH /api/reports/{report_id}",
    "POST /api/reports/{report_id}/revalidate",
    "POST /api/reports/{report_id}/merge",
    "POST /api/dump-sites/{site_id}/cleaned",
    "POST /api/dump-sites/{site_id}/laabal",
    "PATCH /api/dump-sites/{site_id}",
}
PUBLIC_WRITES = {"POST /api/reports", "POST /api/auth/login", "POST /api/auth/logout"}


def write_routes() -> list[tuple[str, str]]:
    """Toutes les routes d'écriture, lues dans le schéma OpenAPI de l'application (rien n'est oublié)."""
    from salubri_api.main import app

    app.openapi_schema = None
    paths = app.openapi()["paths"]
    return sorted((m.upper(), p) for p, ops in paths.items() for m in ops if m in ("post", "put", "patch", "delete"))


def fill(path: str) -> str:
    return re.sub(r"\{[^}]+\}", lambda _: str(uuid.uuid4()), path)


def make_user(db, login: str, role: str, password: str = "motdepasse-123", active: bool = True) -> User:  # type: ignore[no-untyped-def]
    u = User(login=login, display_name=login.title(), role=role, password_hash=hash_password(password), active=active)
    db.add(u)
    db.commit()
    return u


def bearer(client: TestClient, login: str, password: str = "motdepasse-123") -> dict[str, str]:
    r = client.post("/api/auth/login", json={"login": login, "password": password}, headers={"X-Salubri-Token": ""})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture()
def anon(db):  # type: ignore[no-untyped-def]
    from salubri_api.main import app

    with TestClient(app) as c:
        yield c


def test_every_write_route_is_classified():
    routes = {f"{m} {p}" for m, p in write_routes()}
    assert len(routes) >= 19
    assert MODERATION <= routes and PUBLIC_WRITES <= routes


def test_each_write_route_401_anonymous_403_wrong_role_ok_right_role(db, anon):  # type: ignore[no-untyped-def]
    make_user(db, "modo", "moderateur")
    make_user(db, "chef", "admin")
    mod, adm = bearer(anon, "modo"), bearer(anon, "chef")
    checked = 0
    for method, path in write_routes():
        key = f"{method} {path}"
        if key in PUBLIC_WRITES:
            continue
        url = fill(path)
        assert anon.request(method, url, json={}).status_code == 401, f"{key} ouvert aux anonymes"
        as_mod = anon.request(method, url, json={}, headers=mod).status_code
        as_adm = anon.request(method, url, json={}, headers=adm).status_code
        if key in MODERATION:
            assert as_mod not in (401, 403), f"{key} refusé au modérateur ({as_mod})"
        else:
            assert as_mod == 403, f"{key} devrait être réservé à l'admin (modérateur : {as_mod})"
        assert as_adm not in (401, 403), f"{key} refusé à l'admin ({as_adm})"
        checked += 1
    assert checked >= 16


def test_moderation_and_admin_actions_succeed_and_are_signed_in_the_journal(db, anon, client, world):  # type: ignore[no-untyped-def]
    from conftest import free_point, post_report

    make_user(db, "awa", "moderateur")
    make_user(db, "issa", "admin")
    mod, adm = bearer(anon, "awa"), bearer(anon, "issa")
    rid = post_report(anon, free_point(world, n=31), None, client_id="acc-1")["id"]
    r = anon.patch(f"/api/reports/{rid}", json={"status": "verified", "actor": "quelqu'un d'autre"}, headers=mod)
    assert r.status_code == 200 and r.json()["properties"]["moderated_by"] == "awa"
    sid = anon.get("/api/scenarios").json()[0]["id"]
    assert anon.post(f"/api/scenarios/{sid}/recompute", json={}, headers=adm).status_code == 200
    db.expire_all()
    actors = {a.action: a.actor for a in db.query(AuditLog).filter(AuditLog.action.in_(["moderate", "login"]))}
    assert actors["moderate"] == "awa (moderateur)"
    journal = anon.get("/api/audit").json()
    assert any(e["actor"] == "awa (moderateur)" for e in (journal["items"] if isinstance(journal, dict) else journal))


def test_login_me_logout_and_session_rules(db, anon):  # type: ignore[no-untyped-def]
    u = make_user(db, "Mariam", "admin")  # login enregistré tel quel puis comparé en minuscules
    u.login = "mariam"
    db.commit()
    assert anon.post("/api/auth/login", json={"login": "mariam", "password": "faux-faux-faux"}).status_code == 401
    assert anon.post("/api/auth/login", json={"login": "inconnu", "password": "motdepasse-123"}).status_code == 401
    h = bearer(anon, "MARIAM ")
    me = anon.get("/api/auth/me", headers=h).json()
    assert me["login"] == "mariam" and me["role"] == "admin" and me["kind"] == "user"
    assert anon.get("/api/auth/me").status_code == 401
    assert anon.post("/api/auth/logout", headers=h).status_code == 204
    assert anon.get("/api/auth/me", headers=h).status_code == 401  # session fermée


def test_expired_tampered_and_disabled(db, anon):  # type: ignore[no-untyped-def]
    u = make_user(db, "ali", "admin")
    old, _ = issue_token(u, now=time.time() - 9 * 3600)
    assert anon.get("/api/auth/me", headers={"Authorization": f"Bearer {old}"}).status_code == 401
    good, _ = issue_token(u)
    body, sig = good.split(".")
    forged = body[:-2] + ("A" if body[-2] != "A" else "B") + body[-1] + "." + sig
    assert anon.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401
    assert anon.get("/api/auth/me", headers={"Authorization": f"Bearer {good}"}).status_code == 200
    u.active = False
    u.session_version += 1
    db.commit()
    assert anon.get("/api/auth/me", headers={"Authorization": f"Bearer {good}"}).status_code == 401
    assert anon.post("/api/auth/login", json={"login": "ali", "password": "motdepasse-123"}).status_code == 401


def test_service_token_is_admin_and_wrong_token_is_rejected(db, anon):  # type: ignore[no-untyped-def]
    sid = anon.get("/api/scenarios").json()[0]["id"]
    ok = anon.post(f"/api/scenarios/{sid}/recompute", json={}, headers={"X-Salubri-Token": "test-token"})
    assert ok.status_code == 200
    bad = anon.post(f"/api/scenarios/{sid}/recompute", json={}, headers={"X-Salubri-Token": "faux"})
    assert bad.status_code == 401


def test_cli_add_passwd_disable_list(db, capsys, monkeypatch):  # type: ignore[no-untyped-def]
    import io

    from salubri_api.users import main

    monkeypatch.setattr("sys.stdin", io.StringIO("premier-mdp-1\n"))
    assert main(["add", "Fatou", "--role", "moderateur", "--name", "Fatou K.", "--password-stdin"]) == 0
    monkeypatch.setattr("sys.stdin", io.StringIO("court\n"))
    with pytest.raises(SystemExit):
        main(["passwd", "fatou", "--password-stdin"])
    monkeypatch.setattr("sys.stdin", io.StringIO("second-mdp-2\n"))
    assert main(["passwd", "fatou", "--password-stdin"]) == 0
    assert main(["disable", "fatou"]) == 0
    main(["list"])
    out = capsys.readouterr().out
    assert "fatou" in out and "désactivé" in out
    db.expire_all()
    u = db.query(User).filter(User.login == "fatou").one()
    assert not u.active and u.session_version == 2 and u.display_name == "Fatou K."
