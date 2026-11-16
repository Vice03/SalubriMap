# SPDX-License-Identifier: AGPL-3.0-or-later
"""Connexion des comptes de la mairie (modérateur, administrateur). Les citoyens n'ont pas de compte."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from salubri_api.db import get_session
from salubri_api.models import User
from salubri_api.models.audit import audit
from salubri_api.routers.deps import current_user
from salubri_api.services.auth import ROLE_LABEL, Principal, authenticate, issue_token, user_out

router = APIRouter(prefix="/auth", tags=["Connexion"])


class LoginIn(BaseModel):
    login: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


@router.post("/login", summary="Se connecter : renvoie un jeton de session (en-tête Authorization: Bearer …)")
def login(body: LoginIn, s: Session = Depends(get_session)) -> dict[str, Any]:
    user = authenticate(s, body.login, body.password)
    if user is None:
        audit(s, "login_failed", "user", None, after={"login": body.login.strip().lower()[:64]}, actor="anonyme")
        s.commit()
        raise HTTPException(401, "Identifiant ou mot de passe incorrect")
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
