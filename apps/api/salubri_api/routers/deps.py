# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared router dependencies."""

import uuid

from fastapi import Depends, HTTPException
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
