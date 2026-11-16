# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared router dependencies."""

import uuid
from collections.abc import Awaitable, Callable

from fastapi import Depends, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from salubri_api.config import get_settings
from salubri_api.db import get_session, get_sessionmaker
from salubri_api.models import Commune
from salubri_api.services.auth import (
    GRANTS,
    ROLE_LABEL,
    AuthError,
    Principal,
    current_principal,
    principal_from_headers,
)


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


def _resolve(authorization: str | None, service_token: str | None) -> Principal | None:
    with get_sessionmaker()() as s:
        p = principal_from_headers(s, authorization, service_token)
        s.commit()  # rehash éventuel
        return p


async def _principal(authorization: str | None, service_token: str | None) -> Principal | None:
    try:
        p = await run_in_threadpool(_resolve, authorization, service_token)
    except AuthError as exc:
        raise HTTPException(401, exc.message, headers={"WWW-Authenticate": "Bearer"}) from exc
    current_principal.set(p)  # lu par audit() pour signer le journal
    return p


def require_role(role: str) -> Callable[..., Awaitable[Principal | None]]:
    """Dépendance : les écritures exigent un compte ayant `role` (l'admin a aussi les droits du modérateur).

    Les lectures (GET) restent publiques. Utilisée au niveau d'un routeur ou d'une route.
    """

    async def dep(
        request: Request,
        authorization: str | None = Header(None),
        x_salubri_token: str | None = Header(None),
    ) -> Principal | None:
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return None
        p = await _principal(authorization, x_salubri_token)
        if p is None:
            raise HTTPException(
                401,
                "Connectez-vous avec un compte de la mairie pour cette action",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if p.role not in GRANTS[role]:
            need = "administrateur" if role == "admin" else "modérateur ou administrateur"
            raise HTTPException(403, f"Action réservée au rôle {need} (vous êtes {ROLE_LABEL[p.role]})")
        return p

    dep.__name__ = f"require_{role}"
    return dep


require_moderateur = require_role("moderateur")
require_admin = require_role("admin")


async def current_user(
    authorization: str | None = Header(None), x_salubri_token: str | None = Header(None)
) -> Principal:
    """Appelant connecté, quelle que soit la méthode (pour /auth/me et /auth/logout)."""
    p = await _principal(authorization, x_salubri_token)
    if p is None:
        raise HTTPException(401, "Non connecté", headers={"WWW-Authenticate": "Bearer"})
    return p
