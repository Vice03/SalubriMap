# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared router dependencies."""

import hmac
import uuid

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from salubri_api.config import get_settings
from salubri_api.db import get_session
from salubri_api.models import Commune


def get_commune(s: Session = Depends(get_session)) -> Commune:
    c = s.query(Commune).filter(Commune.slug == get_settings().commune).first()
    if c is None:
        raise HTTPException(503, "Commune non chargée : lancer le seed (docker compose run --rm seed)")
    return c


def parse_uuid(value: str, what: str = "identifiant") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(404, f"{what} inconnu : {value}") from exc


def require_mairie(request: Request, x_salubri_token: str | None = Header(None)) -> None:
    """Écritures réservées à la mairie (modération, imports, scénarios, flotte, dépotoirs).

    Les lectures restent publiques ; l'envoi d'un signalement citoyen (POST /api/reports) n'a pas de dépendance.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    expected = get_settings().admin_token
    if not expected:
        return
    if not x_salubri_token or not hmac.compare_digest(x_salubri_token, expected):
        raise HTTPException(
            401, "Code d'accès mairie requis pour cette action", headers={"WWW-Authenticate": "X-Salubri-Token"}
        )
