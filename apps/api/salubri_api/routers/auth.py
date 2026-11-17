# SPDX-License-Identifier: AGPL-3.0-or-later
"""Connexion des comptes de la mairie (modérateur, administrateur). Les citoyens n'ont pas de compte."""

import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from salubri_api.db import get_session
from salubri_api.models import User
from salubri_api.models.audit import audit
from salubri_api.routers.deps import current_user
from salubri_api.services.auth import ROLE_LABEL, Principal, authenticate, issue_token, user_out
from salubri_api.services.ratelimit import (
    client_ip,
    failure_delay_s,
    login_blocked,
    record_login_failure,
    record_login_success,
)

sleep = time.sleep  # remplacé dans les tests (délai sur les échecs répétés d'un même login)

router = APIRouter(prefix="/auth", tags=["Connexion"])


class LoginIn(BaseModel):
    login: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


@router.post("/login", summary="Se connecter : renvoie un jeton de session (en-tête Authorization: Bearer …)")
def login(body: LoginIn, request: Request, s: Session = Depends(get_session)) -> dict[str, Any]:
    name = body.login.strip().lower()[:64]
    ip = client_ip(request.headers, request.client.host if request.client else None)
    wait = login_blocked(s, name, ip)
    if wait:
        minutes = max(1, round(wait / 60))
        raise HTTPException(
            429,
            f"Trop de tentatives de connexion. Réessayez dans {minutes} min.",
            headers={"Retry-After": str(wait)},
        )
    user = authenticate(s, body.login, body.password)
    if user is None:
        delay = failure_delay_s(s, name)
        record_login_failure(s, name, ip)
        audit(s, "login_failed", "user", None, after={"login": name}, actor="anonyme")
        s.commit()
        if delay:
            sleep(delay)  # ralentit l'attaque sur ce login sans bloquer son titulaire
        raise HTTPException(401, "Identifiant ou mot de passe incorrect")
    record_login_success(s, name, ip)
    token, exp = issue_token(user)
    audit(s, "login", "user", user.id, actor=f"{user.login} ({user.role})")
    s.commit()
    return {
        "token": token,
        "token_type": "bearer",
        "expires_at": datetime.fromtimestamp(exp, UTC).isoformat(),
        "user": user_out(user),
    }


@router.post("/logout", status_code=204, summary="Se déconnecter : ferme toutes les sessions de ce compte")
def logout(who: Principal = Depends(current_user), s: Session = Depends(get_session)) -> Response:
    if who.kind == "user":
        user = s.query(User).filter(User.login == who.login).first()
        if user is not None:
            user.session_version += 1
            audit(s, "logout", "user", user.id)
            s.commit()
    return Response(status_code=204)


@router.get("/me", summary="Compte connecté (401 si personne n'est connecté)")
def me(who: Principal = Depends(current_user)) -> dict[str, Any]:
    return {
        "login": who.login,
        "display_name": who.display_name,
        "role": who.role,
        "role_label": ROLE_LABEL[who.role],
        "kind": who.kind,
    }
