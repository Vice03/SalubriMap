# SPDX-License-Identifier: AGPL-3.0-or-later
"""A2 — pas de secret par défaut hors démonstration ; le mode démonstration reste « une commande »."""

import pytest
from fastapi.testclient import TestClient

from salubri_api.config import DEMO_TOKEN, Settings, service_token
from salubri_api.models import User
from salubri_api.services.auth import hash_password
from salubri_api.services.security_config import InsecureConfig, check_startup, ensure_demo_account, problems

GOOD = {"demo_mode": False, "admin_token": "x" * 24, "secret_key": "k" * 40}


def prod(**kw) -> Settings:  # type: ignore[no-untyped-def]
    return Settings(**{**GOOD, **kw})


def add_admin(db, login: str = "chef", active: bool = True) -> None:  # type: ignore[no-untyped-def]
    db.add(
        User(login=login, display_name=login, role="admin", password_hash=hash_password("motdepasse-1"), active=active)
    )
    db.commit()


def test_production_refuses_every_default_secret(db):  # type: ignore[no-untyped-def]
    add_admin(db)
    assert problems(prod(), db) == []
    assert any("vide" in p for p in problems(prod(admin_token=""), db))
    assert any(DEMO_TOKEN in p for p in problems(prod(admin_token=DEMO_TOKEN), db))
    assert any("trop court" in p for p in problems(prod(admin_token="court"), db))
    assert any("SALUBRI_SECRET_KEY" in p for p in problems(prod(secret_key=""), db))
    with pytest.raises(InsecureConfig, match="Démarrage refusé"):
        check_startup(prod(admin_token=DEMO_TOKEN), db)
    check_startup(prod(), db)  # configuration correcte : démarre


def test_production_needs_an_active_admin_and_no_demo_account(db):  # type: ignore[no-untyped-def]
    assert any("aucun compte admin" in p for p in problems(prod(), db))
    add_admin(db, "ancien", active=False)
    assert any("aucun compte admin" in p for p in problems(prod(), db))
    add_admin(db, "chef")
    assert problems(prod(), db) == []
    ensure_demo_account(db)
    assert any("demo" in p for p in problems(prod(), db))


def test_demo_mode_creates_demo_account_once_and_keeps_the_demo_code(db):  # type: ignore[no-untyped-def]
    demo = Settings(demo_mode=True, admin_token="", secret_key="")
    assert problems(demo, db) == [] and service_token(demo) == DEMO_TOKEN
    assert service_token(prod()) == "x" * 24 and service_token(prod(admin_token="")) == ""
    check_startup(demo, db)
    check_startup(demo, db)
    assert db.query(User).filter(User.login == "demo").count() == 1


def test_default_admin_is_created_in_demo_mode_repaired_in_demo_and_blocks_production(db):  # type: ignore[no-untyped-def]
    from salubri_api.services.auth import verify_password

    demo = Settings(demo_mode=True, admin_token="", secret_key="")
    check_startup(demo, db)
    check_startup(demo, db)
    admin = db.query(User).filter(User.login == "admin").one()
    assert admin.role == "admin" and verify_password(admin.password_hash, "Salubri2026")
    assert any("mot de passe par défaut" in p for p in problems(prod(), db))
    admin.password_hash = hash_password("un-autre-mot-de-passe")
    admin.active = False
    db.commit()
    check_startup(demo, db)  # mode démo : compte réparé (réactivé, mot de passe d'origine)
    admin = db.query(User).filter(User.login == "admin").one()
    assert admin.active and verify_password(admin.password_hash, "Salubri2026")


def test_default_admin_logs_in(db):  # type: ignore[no-untyped-def]
    from salubri_api.main import app

    with TestClient(app) as c:
        r = c.post("/api/auth/login", json={"login": "admin", "password": "Salubri2026"})
        assert r.status_code == 200 and r.json()["user"]["role"] == "admin"


def test_demo_account_logs_in_and_health_shows_demo_mode(db):  # type: ignore[no-untyped-def]
    from salubri_api.main import app

    with TestClient(app) as c:  # le démarrage (mode démo dans les tests) crée le compte
        r = c.post("/api/auth/login", json={"login": "demo", "password": DEMO_TOKEN})
        assert r.status_code == 200 and r.json()["user"]["role"] == "admin"
        assert c.get("/api/health").json()["demo_mode"] is True


def test_bootstrap_admin_makes_a_fresh_production_start_possible(db):  # type: ignore[no-untyped-def]
    from salubri_api.services.auth import verify_password
    from salubri_api.services.security_config import bootstrap_admin

    demo = Settings(demo_mode=True, admin_token="", secret_key="")
    check_startup(demo, db)  # base « héritée » d'une démonstration : demo + admin / Salubri2026
    st = prod(bootstrap_admin_password="Premier-mdp-2026")
    assert problems(st, db)  # sans amorçage, démarrage refusé
    assert bootstrap_admin(db, st)
    admin = db.query(User).filter(User.login == "admin").one()
    assert verify_password(admin.password_hash, "Premier-mdp-2026") and admin.active
    assert not db.query(User).filter(User.login == "demo", User.active.is_(True)).count()
    assert problems(st, db) == []
    assert not bootstrap_admin(db, st)  # second passage : rien à faire
    admin.password_hash = hash_password("reste-d-un-ancien-lancement")
    db.commit()
    assert bootstrap_admin(db, st)  # .env fait foi : la base d'un lancement précédent reprend son mot de passe
    assert verify_password(db.query(User).filter(User.login == "admin").one().password_hash, "Premier-mdp-2026")
    assert not bootstrap_admin(db, prod(bootstrap_admin_password="court"))
