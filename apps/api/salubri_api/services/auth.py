# SPDX-License-Identifier: AGPL-3.0-or-later
"""Authentification des comptes mairie et identité de l'appelant.

- Mots de passe : argon2id (argon2-cffi).
- Sessions : jeton signé HMAC-SHA256 (`base64url(json).signature`) avec expiration (8 h par défaut) et
  numéro de version de session : la déconnexion, un changement de mot de passe ou la désactivation du
  compte invalident toutes les sessions déjà délivrées.
- Identifiant de service : l'en-tête `X-Salubri-Token` (SALUBRI_ADMIN_TOKEN) donne les droits admin aux
  scripts (répétition, banc d'essai). Ce n'est pas une session : rien n'est délivré au navigateur.
"""

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from contextvars import ContextVar
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy.orm import Session

from salubri_api.config import get_settings
from salubri_api.config import service_token as effective_service_token
from salubri_api.models import User

log = logging.getLogger(__name__)
_hasher = PasswordHasher()
# hachage factice : vérifié quand le login est inconnu, pour que la réponse prenne le même temps
_DUMMY_HASH = _hasher.hash(secrets.token_hex(16))
_process_key = secrets.token_bytes(32)

# Rôle requis ⊆ rôles qui l'accordent (l'admin peut tout ce que peut le modérateur)
GRANTS = {"moderateur": {"moderateur", "admin"}, "admin": {"admin"}}
ROLE_LABEL = {"moderateur": "modérateur", "admin": "administrateur"}


@dataclass(frozen=True)
class Principal:
    login: str
    role: str
    display_name: str
    kind: str = "user"  # "user" (compte) ou "service" (X-Salubri-Token)

    @property
    def label(self) -> str:
        """Ce qui est écrit dans le journal : « login (rôle) »."""
        return f"{self.login} ({self.role})"[:64]


# Appelant de la requête en cours : lu par audit() pour signer le journal (posé par les dépendances de rôle)
current_principal: ContextVar[Principal | None] = ContextVar("current_principal", default=None)


class AuthError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Le mot de passe doit faire au moins 8 caractères")
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def _key() -> bytes:
    k = get_settings().secret_key
    return hashlib.sha256(k.encode()).digest() if k else _process_key


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def issue_token(user: User, now: float | None = None) -> tuple[str, int]:
    """Jeton de session signé ; renvoie (jeton, expiration en secondes epoch)."""
    exp = int((now or time.time()) + get_settings().session_hours * 3600)
    body = _b64(
        json.dumps({"sub": str(user.id), "sv": user.session_version, "exp": exp}, separators=(",", ":")).encode()
    )
    sig = _b64(hmac.new(_key(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}", exp


def read_token(token: str, now: float | None = None) -> dict[str, object]:
    try:
        body, sig = token.split(".", 1)
        good = hmac.compare_digest(_b64(hmac.new(_key(), body.encode(), hashlib.sha256).digest()), sig)
        payload = json.loads(_unb64(body)) if good else None
    except (ValueError, json.JSONDecodeError):
        payload = None
    if not isinstance(payload, dict):
        raise AuthError("Session invalide : reconnectez-vous")
    if int(payload.get("exp", 0)) < (now or time.time()):
        raise AuthError("Session expirée : reconnectez-vous")
    return payload


def authenticate(s: Session, login: str, password: str) -> User | None:
    user = s.query(User).filter(User.login == login.strip().lower()).first()
    ok = verify_password(user.password_hash if user else None, password)
    if not ok or user is None or not user.active:
        return None
    if _hasher.check_needs_rehash(user.password_hash):
        user.password_hash = _hasher.hash(password)
    return user


def principal_from_headers(s: Session, authorization: str | None, service_token: str | None) -> Principal | None:
    """Identité de l'appelant ; None si anonyme. Lève AuthError si un identifiant est présent mais invalide."""
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AuthError("En-tête Authorization attendu : « Bearer <jeton> »")
        payload = read_token(token.strip())
        user = s.get(User, __import__("uuid").UUID(str(payload["sub"])))
        if user is None or not user.active or user.session_version != payload.get("sv"):
            raise AuthError("Session fermée ou compte désactivé : reconnectez-vous")
        return Principal(user.login, user.role, user.display_name)
    if service_token:
        expected = effective_service_token(get_settings())
        if expected and hmac.compare_digest(service_token, expected):
            return Principal("service", "admin", "Identifiant de service")
        raise AuthError("Code d'accès invalide")
    return None


def user_out(u: User) -> dict[str, object]:
    return {
        "login": u.login,
        "display_name": u.display_name,
        "role": u.role,
        "role_label": ROLE_LABEL[u.role],
        "active": u.active,
    }
