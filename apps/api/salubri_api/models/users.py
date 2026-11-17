# SPDX-License-Identifier: AGPL-3.0-or-later
"""Comptes de la mairie (modérateurs, administrateurs). Les citoyens n'ont pas de compte."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from salubri_api.models import Base, new_id, utcnow

ROLES = ("moderateur", "admin")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role in ('moderateur','admin')", name="ck_user_role"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    login: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(16))
    password_hash: Mapped[str] = mapped_column(String(256))
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # incrémenté à la déconnexion, au changement de mot de passe et à la désactivation :
    # invalide d'un coup toutes les sessions déjà délivrées à ce compte
    session_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LoginFailure(Base):
    """Échec de connexion (anti-force brute, services/ratelimit.py). En base pour que la commande
    `python -m salubri_api.users unlock` atteigne l'API en cours d'exécution, et pour survivre à un redémarrage."""

    __tablename__ = "login_failures"
    __table_args__ = (Index("ix_login_failures_login_at", "login", "at"), Index("ix_login_failures_ip_at", "ip", "at"))
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    login: Mapped[str] = mapped_column(String(64))
    ip: Mapped[str] = mapped_column(String(64))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
