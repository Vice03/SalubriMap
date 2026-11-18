# SPDX-License-Identifier: AGPL-3.0-or-later
"""Brigade Laabal : transmission automatique des dépotoirs récidivistes et zones en alerte.

Un dépotoir est *récidiviste* quand il revient après avoir été nettoyé (statut `recurring`, fenêtre
RECURRING_DAYS). Chaque retour est transmis une fois à la brigade, automatiquement (journal : action
`laabal_alert`, acteur `auto`). Un quartier est *en alerte* dès qu'il contient un dépotoir récidiviste,
*critique* à partir de CRITICAL. La brigade contrôle, sensibilise et sanctionne : elle ne ramasse pas.

Le message à la brigade part par un lien WhatsApp (wa.me) ouvert par l'agent : rien n'est envoyé sans clic,
aucune dépendance à un service extérieur (sans réseau, le message se copie)."""

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api.config import get_settings
from salubri_api.models import DumpSite
from salubri_api.models.audit import AuditLog, audit
from salubri_api.services.geo import shape

CRITICAL = 3
PLACEHOLDER = "+22600000000"


def _last_alert(s: Session, site_id: uuid.UUID) -> AuditLog | None:
    return (
        s.query(AuditLog)
        .filter(AuditLog.action == "laabal_alert", AuditLog.entity == "dump_site", AuditLog.entity_id == str(site_id))
        .order_by(AuditLog.at.desc())
        .first()
    )


def auto_transmit(s: Session, commune_id: uuid.UUID) -> int:
    """Transmet à la brigade chaque dépotoir récidiviste pas encore transmis depuis son dernier nettoyage."""
    if not get_settings().laabal_auto:
        return 0
    n = 0
    for d in s.query(DumpSite).filter(DumpSite.commune_id == commune_id, DumpSite.status == "recurring").all():
        last = _last_alert(s, d.id)
        if last is not None and (d.cleaned_at is None or last.at >= d.cleaned_at):
            continue
        audit(s, "laabal_alert", "dump_site", d.id, after={"auto": True, "recurring": True,
                                                         "caniveau": bool(d.near_drain)}, actor="auto")  # fmt: skip
        n += 1
    if n:
        s.flush()
    return n


def zones(s: Session, commune_id: uuid.UUID) -> dict[str, Any]:
    st = get_settings()
    rows = s.execute(
        text("""SELECT d.id, q.name AS quartier, q.arrondissement
                FROM dump_sites d LEFT JOIN quartiers q
                  ON q.commune_id = d.commune_id AND ST_Contains(q.geom, d.geom)
                WHERE d.commune_id = :c AND d.status = 'recurring'"""),
        {"c": commune_id},
    ).all()
    by_q: dict[str, dict[str, Any]] = {}
    for r in rows:
        d = s.get(DumpSite, r.id)
        if d is None:
            continue
        p = shape_point(d)
        last = _last_alert(s, d.id)
        z = by_q.setdefault(r.quartier or "Hors quartier", {"quartier": r.quartier or "Hors quartier",
                                                            "arrondissement": r.arrondissement, "sites": []})  # fmt: skip
        z["sites"].append({
            "id": str(d.id), "lat": round(p[1], 6), "lon": round(p[0], 6), "volume_m3": d.volume_est_m3,
            "type": d.dominant_type, "n_signalements": d.n_reports, "caniveau": bool(d.near_drain),
            "nettoye_le": d.cleaned_at.isoformat() if d.cleaned_at else None,
            "revu_le": d.last_reported_at.isoformat(),
            "transmis_le": last.at.isoformat() if last else None, "auto": bool(last and last.actor == "auto"),
        })  # fmt: skip
    out = []
    for z in by_q.values():
        n = len(z["sites"])
        z["recidivistes"] = n
        z["niveau"] = "critique" if n >= CRITICAL else "alerte"
        z["caniveaux"] = sum(1 for x in z["sites"] if x["caniveau"])
        out.append(z)
    out.sort(key=lambda z: (-z["recidivistes"], -z["caniveaux"], z["quartier"]))
    return {"numero": st.laabal_whatsapp, "numero_demo": st.laabal_whatsapp.replace(" ", "") == PLACEHOLDER,
            "auto": st.laabal_auto, "zones": out}  # fmt: skip


def shape_point(d: DumpSite) -> tuple[float, float]:
    g = shape(d.geom)
    return (g.x, g.y)
