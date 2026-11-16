# SPDX-License-Identifier: AGPL-3.0-or-later
"""Garde-fous de démarrage : pas de secret par défaut hors mode démonstration.

- Mode démonstration (SALUBRI_DEMO_MODE=true, réglage de docker-compose.yml) : le compte « demo » (admin, mot de
  passe ouaga2026) est créé s'il manque et le code de service vaut ouaga2026 si aucun n'est fourni. L'interface
  affiche un badge « Mode démonstration ».
- Hors démonstration : l'API refuse de démarrer si le code de service est vide ou vaut ouaga2026, si la clé de
  signature des sessions est vide, ou s'il n'existe aucun compte admin actif. `run/start` génère les secrets dans
  .env au premier démarrage ; `run/admin` crée le premier compte admin.
"""

import logging

from sqlalchemy.orm import Session

from salubri_api.config import DEMO_TOKEN, Settings
from salubri_api.models import User
from salubri_api.models.audit import audit
from salubri_api.services.auth import hash_password

log = logging.getLogger(__name__)
DEMO_LOGIN = "demo"
DEMO_PASSWORD = DEMO_TOKEN


class InsecureConfig(RuntimeError):
    pass


def problems(settings: Settings, s: Session) -> list[str]:
    """Ce qui empêche un démarrage hors démonstration (liste vide = configuration acceptable)."""
    if settings.demo_mode:
        return []
    out = []
    if not settings.admin_token:
        out.append("SALUBRI_ADMIN_TOKEN est vide : définissez un code de service (run/start le génère dans .env)")
    elif settings.admin_token == DEMO_TOKEN:
        out.append(f"SALUBRI_ADMIN_TOKEN vaut le code de démonstration « {DEMO_TOKEN} », connu de tous : changez-le")
    elif len(settings.admin_token) < 16:
        out.append("SALUBRI_ADMIN_TOKEN est trop court : 16 caractères au moins")
    if len(settings.secret_key) < 32:
        out.append(
            "SALUBRI_SECRET_KEY est vide ou trop courte (32 caractères au moins) : run/start la génère dans .env"
        )
    admins = s.query(User).filter(User.role == "admin", User.active.is_(True)).count()
    if not admins:
        out.append(
            "aucun compte admin actif : créez-en un avec run/admin (python -m salubri_api.users add <login> --role admin)"
        )
    demo = s.query(User).filter(User.login == DEMO_LOGIN, User.active.is_(True)).first()
    if demo is not None:
        out.append(
            "le compte de démonstration « demo » est actif : désactivez-le (python -m salubri_api.users disable demo)"
        )
    return out


def ensure_demo_account(s: Session) -> bool:
    """Mode démo : crée le compte admin « demo » (mot de passe ouaga2026) s'il n'existe pas. True si créé."""
    if s.query(User).filter(User.login == DEMO_LOGIN).first() is not None:
        return False
    u = User(login=DEMO_LOGIN, display_name="Démonstration", role="admin", password_hash=hash_password(DEMO_PASSWORD))
    s.add(u)
    s.flush()
    audit(s, "create", "user", u.id, after={"login": DEMO_LOGIN, "role": "admin", "demo": True}, actor="system")
    s.commit()
    return True


def check_startup(settings: Settings, s: Session) -> None:
    if settings.demo_mode:
        if ensure_demo_account(s):
            log.warning("Mode démonstration : compte « demo » créé (mot de passe %s)", DEMO_PASSWORD)
        log.warning("MODE DÉMONSTRATION : compte « demo » et code « %s » connus de tous, ne pas exposer", DEMO_TOKEN)
        return
    found = problems(settings, s)
    if found:
        raise InsecureConfig(
            "Démarrage refusé (SALUBRI_DEMO_MODE=false) :\n - "
            + "\n - ".join(found)
            + "\nPour une démonstration, remettez SALUBRI_DEMO_MODE=true."
        )
