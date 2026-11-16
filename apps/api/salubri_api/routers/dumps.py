# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api.db import get_session
from salubri_api.models import Commune, DumpSite
from salubri_api.models.audit import audit
from salubri_api.routers.deps import get_commune, parse_uuid, require_moderateur
from salubri_api.routers.serializers import dump_feature
from salubri_api.services.consolidation import mark_cleaned
from salubri_api.services.geo import feature_collection
from salubri_api.services.plan.trigger import reports_changed

router = APIRouter(prefix="/dump-sites", tags=["Dépotoirs"], dependencies=[Depends(require_moderateur)])


@router.get("", summary="Dépotoirs consolidés (FeatureCollection, triés par priorité)")
def list_dumps(
    status: Annotated[list[str] | None, Query()] = None,
    bbox: Annotated[str | None, Query(description="minLon,minLat,maxLon,maxLat")] = None,
    s: Session = Depends(get_session),
    commune: Commune = Depends(get_commune),
) -> dict[str, Any]:
    q = s.query(DumpSite).filter(DumpSite.commune_id == commune.id)
    if status:
        q = q.filter(DumpSite.status.in_(status))
    if bbox:
        try:
            x1, y1, x2, y2 = (float(v) for v in bbox.split(","))
        except ValueError as exc:
            raise HTTPException(422, "bbox attendu : minLon,minLat,maxLon,maxLat") from exc
        q = q.filter(text("ST_Intersects(dump_sites.geom, ST_MakeEnvelope(:x1,:y1,:x2,:y2,4326))")).params(
            x1=x1, y1=y1, x2=x2, y2=y2
        )
    return feature_collection([dump_feature(d) for d in q.order_by(DumpSite.priority.desc())])


def _get(s: Session, site_id: str) -> DumpSite:
    d = s.get(DumpSite, parse_uuid(site_id, "dépotoir"))
    if d is None:
        raise HTTPException(404, "Dépotoir introuvable")
    return d


@router.post("/{site_id}/cleaned", summary="Services techniques de la mairie : marquer nettoyé")
def cleaned(
    site_id: str,
    device_id: Annotated[str | None, Form()] = None,
    photo: Annotated[UploadFile | None, File()] = None,
    s: Session = Depends(get_session),
    commune: Commune = Depends(get_commune),
) -> dict[str, Any]:
    d = _get(s, site_id)
    mark_cleaned(s, d)
    audit(
        s,
        "cleaned",
        "dump_site",
        d.id,
        after={"device_id": device_id, "photo": photo is not None},
    )
    s.commit()
    reports_changed(commune.id)
    return dump_feature(d)


@router.post("/{site_id}/laabal", summary="Transmettre à la brigade Laabal (cible de contrôle civique)")
def to_laabal(site_id: str, s: Session = Depends(get_session)) -> dict[str, Any]:
    """La brigade Laabal ne ramasse pas : elle contrôle, sensibilise et sanctionne les riverains."""
    d = _get(s, site_id)
    audit(s, "laabal_alert", "dump_site", d.id, after={"recurring": bool(getattr(d, "recurring", False))})
    s.commit()
    out = dump_feature(d)
    out["properties"]["laabal_alerted"] = True
    return out


class OsmIdIn(BaseModel):
    osm_id: int


@router.patch("/{site_id}", summary="Enregistrer l'identifiant OSM après versement")
def set_osm_id(site_id: str, body: OsmIdIn, s: Session = Depends(get_session)) -> dict[str, Any]:
    d = _get(s, site_id)
    d.osm_id = body.osm_id
    audit(s, "osm_id", "dump_site", d.id, after={"osm_id": body.osm_id})
    s.commit()
    return dump_feature(d)
