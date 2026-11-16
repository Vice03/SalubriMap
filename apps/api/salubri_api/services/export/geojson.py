# SPDX-License-Identifier: AGPL-3.0-or-later
"""Public exports carry no personal data: no device_id, no free-text comment."""

from typing import Any

from salubri_api.models import DumpSite
from salubri_api.services.geo import feature, feature_collection

SITE_KIND = {"decharge_sauvage": "sauvage", "decharge_encadree": "encadree", "autre": "autre"}


def _site_ref(d: DumpSite) -> tuple[str, str | None]:
    """Type de site (sauvage / encadrée / autre) et référence officielle éventuelle (SDGD 2020)."""
    from sqlalchemy.orm import object_session

    from salubri_api.models import Commune, Report
    from salubri_api.services.reference import sdgd_features

    s = object_session(d)
    if s is None:
        return "sauvage", None
    ext = (
        s.query(Report.external_id)
        .filter(Report.dump_site_id == d.id, Report.external_id.like("sdgd2020:%"))
        .limit(1)
        .scalar()
    )
    if not ext:
        return "sauvage", None
    sid = ext.split(":", 1)[1]
    slug = s.query(Commune.slug).filter(Commune.id == d.commune_id).scalar() or ""
    statut = next((f["properties"]["statut"] for f in sdgd_features(slug) if f["properties"]["id"] == sid), "")
    return SITE_KIND.get(statut, "sauvage"), f"SDGD 2020 · n° {sid.split('-')[-1]}"


def dump_site_properties(d: DumpSite) -> dict[str, Any]:
    kind, ref = _site_ref(d)
    return {
        "site_kind": kind,
        "ref": ref,
        "id": str(d.id),
        "status": d.status,
        "waste_type": d.dominant_type,
        "volume_est_m3": d.volume_est_m3,
        "n_reports": d.n_reports,
        "first_reported_at": d.first_reported_at.isoformat(),
        "last_reported_at": d.last_reported_at.isoformat(),
        "near_water": d.near_water,
        "priority": d.priority,
        "confidence": d.mean_score,
        "osm_id": d.osm_id,
    }


def dump_sites_geojson(sites: list[DumpSite]) -> dict[str, Any]:
    return feature_collection(
        [feature(d.geom, dump_site_properties(d), d.id) for d in sites],
        license="CC0-1.0",
        attribution="Salubri — signalements vérifiés",
    )
