# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api.db import get_session
from salubri_api.models import Commune, DumpSite, Photo, Report, utcnow
from salubri_api.models.audit import audit
from salubri_api.routers.deps import get_commune, parse_uuid, require_moderateur
from salubri_api.routers.serializers import report_feature
from salubri_api.schemas.reports import MergeIn, ReportCreated, ReportIn, ReportPatch
from salubri_api.services.auth import Principal
from salubri_api.services.consolidation import consolidate
from salubri_api.services.geo import feature_collection, shape
from salubri_api.services.plan.trigger import reports_changed
from salubri_api.services.reports import find_by_client_id, stage_report, thresholds_for, validate_staged
from salubri_api.services.validation.engine import corroborate, photo_info_from_row, validate_report

router = APIRouter(prefix="/reports", tags=["Signalements"])
MAX_PHOTO = 12 * 1024 * 1024


def _created(r: Report, already: bool = False) -> ReportCreated:
    return ReportCreated(
        id=str(r.id),
        status=r.status,
        score=r.score,
        rule_hits=r.rule_hits,  # type: ignore[arg-type]
        duplicate_of=str(r.duplicate_of) if r.duplicate_of else None,
        already_received=already,
    )


@router.post(
    "",
    status_code=201,
    response_model=ReportCreated,
    summary="Envoyer un signalement (Salubri Go)",
    description="Multipart. Idempotent sur `client_id` : un renvoi renvoie 200 et le même signalement.",
)
def create_report(
    response: Response,
    lat: Annotated[float, Form()],
    lon: Annotated[float, Form()],
    waste_type: Annotated[str, Form()] = "other",
    volume_class: Annotated[str, Form()] = "bag",
    accuracy: Annotated[float | None, Form()] = None,
    comment: Annotated[str | None, Form()] = None,
    reported_at: Annotated[datetime | None, Form()] = None,
    device_id: Annotated[str | None, Form()] = None,
    client_id: Annotated[str | None, Form()] = None,
    external_id: Annotated[str | None, Form()] = None,
    photo: Annotated[UploadFile | None, File()] = None,
    s: Session = Depends(get_session),
    commune: Commune = Depends(get_commune),
) -> ReportCreated:
    existing = find_by_client_id(s, client_id)
    if existing is not None:
        response.status_code = 200
        return _created(existing, True)
    try:
        data = ReportIn(
            lat=lat,
            lon=lon,
            waste_type=waste_type,
            volume_class=volume_class,  # type: ignore[arg-type]
            accuracy=accuracy,
            comment=comment,
            reported_at=reported_at,
            device_id=device_id,
            client_id=client_id,
            external_id=external_id,
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc
    raw = photo.file.read(MAX_PHOTO + 1) if photo is not None else None
    if raw is not None and len(raw) > MAX_PHOTO:
        raise HTTPException(413, "Photo trop lourde (12 Mo maximum)")
    try:
        st = stage_report(s, commune, data, raw or None)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    validate_staged(s, commune, [st])
    if st.report.status == "verified":
        consolidate(s, commune.id)
    s.commit()
    reports_changed(commune.id)
    return _created(st.report)


@router.get("", summary="Lister les signalements (FeatureCollection)")
def list_reports(
    status: Annotated[list[str] | None, Query(description="Un ou plusieurs statuts")] = None,
    waste_type: Annotated[list[str] | None, Query(alias="type")] = None,
    quartier: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    bbox: Annotated[str | None, Query(description="minLon,minLat,maxLon,maxLat")] = None,
    min_score: int | None = None,
    max_score: int | None = None,
    rule: Annotated[str | None, Query(description="Code de règle déclenchée, ex. R2")] = None,
    device_id: str | None = None,
    import_batch: str | None = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 1000,
    offset: Annotated[int, Query(ge=0)] = 0,
    s: Session = Depends(get_session),
    commune: Commune = Depends(get_commune),
) -> dict[str, Any]:
    q = s.query(Report).filter(Report.commune_id == commune.id)
    if status:
        q = q.filter(Report.status.in_(status))
    if waste_type:
        q = q.filter(Report.waste_type.in_(waste_type))
    if quartier:
        q = q.filter(Report.quartier_id == parse_uuid(quartier, "quartier"))
    if since:
        q = q.filter(Report.reported_at >= since)
    if until:
        q = q.filter(Report.reported_at <= until)
    if min_score is not None:
        q = q.filter(Report.score >= min_score)
    if max_score is not None:
        q = q.filter(Report.score <= max_score)
    if device_id:
        q = q.filter(Report.device_id == device_id)
    if import_batch:
        q = q.filter(Report.import_batch_id == parse_uuid(import_batch, "import"))
    if rule:
        q = q.filter(Report.rule_hits.contains([{"rule": rule.upper()}]))
    if bbox:
        try:
            x1, y1, x2, y2 = (float(v) for v in bbox.split(","))
        except ValueError as exc:
            raise HTTPException(422, "bbox attendu : minLon,minLat,maxLon,maxLat") from exc
        q = q.filter(text("ST_Intersects(reports.geom, ST_MakeEnvelope(:x1,:y1,:x2,:y2,4326))")).params(
            x1=x1, y1=y1, x2=x2, y2=y2
        )
    total = q.count()
    rows = q.order_by(Report.reported_at.desc()).offset(offset).limit(limit).all()
    photos = {p.report_id: p for p in s.query(Photo).filter(Photo.report_id.in_([r.id for r in rows]))} if rows else {}
    return feature_collection([report_feature(s, r, photos) for r in rows], total=total, limit=limit, offset=offset)


@router.get("/stats", summary="Compteurs par statut, type et règle (tuiles du tableau de bord)")
def stats(s: Session = Depends(get_session), commune: Commune = Depends(get_commune)) -> dict[str, Any]:
    by_status = dict(
        s.execute(
            text("SELECT status, count(*) FROM reports WHERE commune_id=:c GROUP BY status"), {"c": commune.id}
        ).all()
    )
    by_type = dict(
        s.execute(
            text("SELECT waste_type, count(*) FROM reports WHERE commune_id=:c GROUP BY waste_type"), {"c": commune.id}
        ).all()
    )
    by_rule = dict(
        s.execute(
            text("""SELECT h->>'rule', count(*) FROM reports, jsonb_array_elements(rule_hits) h
                                     WHERE commune_id=:c GROUP BY 1"""),
            {"c": commune.id},
        ).all()
    )
    dumps = dict(
        s.execute(
            text("SELECT status, count(*) FROM dump_sites WHERE commune_id=:c GROUP BY status"), {"c": commune.id}
        ).all()
    )
    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
        "by_type": by_type,
        "by_rule": by_rule,
        "dump_sites": dumps,
    }


def _get(s: Session, report_id: str) -> Report:
    r = s.get(Report, parse_uuid(report_id, "signalement"))
    if r is None:
        raise HTTPException(404, "Signalement introuvable")
    return r


@router.get("/{report_id}", summary="Fiche complète d'un signalement")
def get_report(report_id: str, s: Session = Depends(get_session)) -> dict[str, Any]:
    r = _get(s, report_id)
    f = report_feature(s, r)
    related = s.query(Report).filter((Report.duplicate_of == r.id) | (Report.id == r.duplicate_of)).all()
    f["properties"]["related"] = [
        {
            "id": str(x.id),
            "status": x.status,
            "score": x.score,
            "relation": "original" if x.id == r.duplicate_of else "duplicate",
        }
        for x in related
    ]
    if r.dump_site_id:
        d = s.get(DumpSite, r.dump_site_id)
        if d:
            f["properties"]["dump_site"] = {"id": str(d.id), "status": d.status, "n_reports": d.n_reports}
    photo = s.query(Photo).filter(Photo.report_id == r.id).first()
    if photo:
        f["properties"]["photo"] = {
            "width": photo.width,
            "height": photo.height,
            "bytes": photo.bytes,
            "exif_lat": photo.exif_lat,
            "exif_lon": photo.exif_lon,
            "exif_taken_at": photo.exif_taken_at.isoformat() if photo.exif_taken_at else None,
        }
    return f


@router.patch("/{report_id}", summary="Modérer : forcer un statut (journalisé)")
def patch_report(
    report_id: str,
    body: ReportPatch,
    s: Session = Depends(get_session),
    commune: Commune = Depends(get_commune),
    who: Principal = Depends(require_moderateur),
) -> dict[str, Any]:
    r = _get(s, report_id)
    before = {"status": r.status, "score": r.score}
    r.status, r.forced_status = body.status, True
    # l'auteur est le compte connecté (le champ « actor » du corps n'est plus pris en compte)
    r.moderated_by, r.moderated_at = who.login, utcnow()
    audit(s, "moderate", "report", r.id, before, {"status": body.status, "note": body.note})
    s.flush()
    consolidate(s, commune.id)
    s.commit()
    reports_changed(commune.id)
    return report_feature(s, r)


@router.post(
    "/{report_id}/revalidate",
    dependencies=[Depends(require_moderateur)],
    summary="Rejouer les règles R1–R12 sur ce signalement",
)
def revalidate(
    report_id: str, s: Session = Depends(get_session), commune: Commune = Depends(get_commune)
) -> dict[str, Any]:
    r = _get(s, report_id)
    r.forced_status = False
    g = shape(r.geom)
    p = s.query(Photo).filter(Photo.report_id == r.id).first()
    th = thresholds_for(commune)
    validate_report(s, r, g.y, g.x, photo_info_from_row(p) if p else None, th)
    s.flush()
    corroborate(s, r, th)
    consolidate(s, commune.id)
    s.commit()
    reports_changed(commune.id)
    return report_feature(s, r)


@router.post(
    "/{report_id}/merge",
    dependencies=[Depends(require_moderateur)],
    summary="Fusionner dans un autre signalement (doublon confirmé)",
)
def merge(
    report_id: str, body: MergeIn, s: Session = Depends(get_session), commune: Commune = Depends(get_commune)
) -> dict[str, Any]:
    r = _get(s, report_id)
    target = s.get(Report, parse_uuid(body.into, "signalement cible"))
    if target is None:
        raise HTTPException(404, "Signalement cible introuvable")
    before = {"status": r.status, "duplicate_of": str(r.duplicate_of) if r.duplicate_of else None}
    r.duplicate_of, r.status, r.forced_status = target.id, "rejected", True
    r.rule_hits = [*r.rule_hits, {"rule": "MOD", "delta": 0, "detail": f"Fusionné dans {str(target.id)[:8]}"}]
    audit(s, "merge", "report", r.id, before, {"into": str(target.id)})
    s.flush()
    consolidate(s, commune.id)
    s.commit()
    return report_feature(s, r)
