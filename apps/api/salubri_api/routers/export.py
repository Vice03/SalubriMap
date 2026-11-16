# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from salubri_api.db import get_session
from salubri_api.models import Commune, DumpSite
from salubri_api.routers.deps import get_commune
from salubri_api.services.export.csv import dump_sites_csv
from salubri_api.services.export.geojson import dump_sites_geojson
from salubri_api.services.export.osm_xml import dump_sites_osm

router = APIRouter(prefix="/export", tags=["Export"])
Status = Annotated[list[str], Query(description="Statuts de dépotoir : active, recurring, cleaned")]


def _sites(s: Session, commune: Commune, status: list[str], since: datetime | None) -> list[DumpSite]:
    q = s.query(DumpSite).filter(DumpSite.commune_id == commune.id, DumpSite.status.in_(status))
    if since:
        q = q.filter(DumpSite.last_reported_at >= since)
    return q.order_by(DumpSite.priority.desc()).all()


def _status(status: list[str] | None) -> list[str]:
    s = [x for x in (status or ["active", "recurring"]) if x != "verified"]
    return s or ["active", "recurring"]


@router.get("/geojson", summary="Dépotoirs vérifiés en GeoJSON (sans données personnelles)")
def export_geojson(
    status: Status = None,
    since: datetime | None = None,
    s: Session = Depends(get_session),  # type: ignore[assignment]
    commune: Commune = Depends(get_commune),
) -> Response:
    import json

    body = json.dumps(dump_sites_geojson(_sites(s, commune, _status(status), since)), ensure_ascii=False)
    return Response(
        body,
        media_type="application/geo+json",
        headers={"Content-Disposition": 'attachment; filename="salubri-depotoirs.geojson"'},
    )


@router.get("/csv", summary="Dépotoirs vérifiés en CSV (UTF-8 avec BOM, séparateur ;)")
def export_csv(
    status: Status = None,
    since: datetime | None = None,
    s: Session = Depends(get_session),  # type: ignore[assignment]
    commune: Commune = Depends(get_commune),
) -> Response:
    return Response(
        dump_sites_csv(_sites(s, commune, _status(status), since)),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="salubri-depotoirs.csv"'},
    )


@router.get("/osm", summary="Dépotoirs vérifiés en OSM XML pour JOSM (voir docs/OSM.md)")
def export_osm(
    status: Status = None,
    since: datetime | None = None,
    s: Session = Depends(get_session),  # type: ignore[assignment]
    commune: Commune = Depends(get_commune),
) -> Response:
    return Response(
        dump_sites_osm(_sites(s, commune, _status(status), since)),
        media_type="application/xml",
        headers={"Content-Disposition": 'attachment; filename="salubri-depotoirs.osm"'},
    )
