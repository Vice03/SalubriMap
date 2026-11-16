# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sérialisation des signalements et dépotoirs.

Les modérateurs voient tout ; le public ne voit que les signalements vérifiés ou nettoyés, sans appareil,
commentaire, EXIF ni nom du modérateur (lot A4, docs/HYPOTHESES.md).
"""

from typing import Any

from sqlalchemy.orm import Session

from salubri_api.models import DumpSite, Photo, Report
from salubri_api.services.export.geojson import dump_site_properties
from salubri_api.services.geo import feature

PUBLIC_STATUSES = ("verified", "cleaned")
PUBLIC_FIELDS = (
    "id",
    "status",
    "score",
    "waste_type",
    "volume_class",
    "reported_at",
    "dump_site_id",
    "quartier_id",
    "photo_url",
)


def photo_url(r: Report, photo: Photo | None) -> str | None:
    # route de l'API, qui vérifie le statut et le rôle : /photos/ n'est plus servi en direct
    return f"/api/reports/{r.id}/photo" if photo else None


def is_public(r: Report) -> bool:
    return r.status in PUBLIC_STATUSES


def public_properties(props: dict[str, Any]) -> dict[str, Any]:
    return {k: props[k] for k in PUBLIC_FIELDS if k in props}


def report_properties(r: Report, photo: Photo | None) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "status": r.status,
        "score": r.score,
        "rule_hits": r.rule_hits,
        "waste_type": r.waste_type,
        "volume_class": r.volume_class,
        "comment": r.comment,
        "reported_at": r.reported_at.isoformat(),
        "received_at": r.received_at.isoformat(),
        "gps_accuracy_m": r.gps_accuracy_m,
        "device_id": r.device_id,
        "external_id": r.external_id,
        "duplicate_of": str(r.duplicate_of) if r.duplicate_of else None,
        "dump_site_id": str(r.dump_site_id) if r.dump_site_id else None,
        "quartier_id": str(r.quartier_id) if r.quartier_id else None,
        "import_batch_id": str(r.import_batch_id) if r.import_batch_id else None,
        "photo_url": photo_url(r, photo),
        "forced_status": r.forced_status,
        "moderated_by": r.moderated_by,
        "moderated_at": r.moderated_at.isoformat() if r.moderated_at else None,
    }


def report_feature(s: Session, r: Report, photos: dict[Any, Photo] | None = None, staff: bool = True) -> dict[str, Any]:
    photo = photos.get(r.id) if photos is not None else s.query(Photo).filter(Photo.report_id == r.id).first()
    props = report_properties(r, photo)
    return feature(r.geom, props if staff else public_properties(props), r.id)


def dump_feature(d: DumpSite) -> dict[str, Any]:
    return feature(d.geom, dump_site_properties(d), d.id)
