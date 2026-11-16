# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from salubri_api.db import get_session
from salubri_api.models import AuditLog
from salubri_api.routers.deps import require_staff_read

# le journal contient des identifiants d'appareil, des notes et des noms de comptes : réservé à la mairie (lot A4)
router = APIRouter(prefix="/audit", tags=["Journal"], dependencies=[Depends(require_staff_read)])


@router.get("", summary="Journal d'audit (plus récent d'abord)")
def list_audit(
    entity: str | None = None, limit: Annotated[int, Query(ge=1, le=1000)] = 200, s: Session = Depends(get_session)
) -> list[dict[str, Any]]:
    q = s.query(AuditLog)
    if entity:
        q = q.filter(AuditLog.entity == entity)
    return [
        {
            "id": str(a.id),
            "actor": a.actor,
            "action": a.action,
            "entity": a.entity,
            "entity_id": a.entity_id,
            "before": a.before,
            "after": a.after,
            "at": a.at.isoformat(),
        }
        for a in q.order_by(AuditLog.at.desc()).limit(limit)
    ]
