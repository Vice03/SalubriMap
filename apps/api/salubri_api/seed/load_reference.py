# SPDX-License-Identifier: AGPL-3.0-or-later
"""Charge les décharges du SDGD 2020 comme signalements officiels vérifiés (idempotent)."""

from datetime import timedelta

from shapely.geometry import Point
from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api.models import Commune, Report, utcnow
from salubri_api.services.geo import to_wkb
from salubri_api.services.reference import DUMP_STATUTS, sdgd_features


def load_sdgd_dumps(s: Session, commune: Commune) -> int:
    known = {
        r[0]
        for r in s.query(Report.external_id).filter(
            Report.commune_id == commune.id, Report.external_id.like("sdgd2020:%")
        )
    }
    n = 0
    when = utcnow() - timedelta(days=7)
    for f in sdgd_features(commune.slug):
        pr = f["properties"]
        ext = f"sdgd2020:{pr['id']}"
        if pr.get("statut") not in DUMP_STATUTS or ext in known:
            continue
        lon, lat = f["geometry"]["coordinates"][:2]
        q = s.execute(
            text("""SELECT id FROM quartiers WHERE commune_id = :c
                    AND ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)) LIMIT 1"""),
            {"c": commune.id, "lon": lon, "lat": lat},
        ).scalar()
        s.add(
            Report(
                commune_id=commune.id,
                external_id=ext,
                geom=to_wkb(Point(lon, lat)),
                gps_accuracy_m=float(pr.get("precision_m", 500)),
                waste_type="mixed",
                volume_class="more",
                comment=f"{pr.get('libelle')} — relevé SDGD Ouagadougou 2019 (rapport mars 2020), position numérisée",
                reported_at=when,
                status="verified",
                score=100,
                forced_status=True,
                moderated_by="SDGD 2020 (source officielle)",
                moderated_at=utcnow(),
                quartier_id=q,
            )
        )
        n += 1
    s.flush()
    return n
