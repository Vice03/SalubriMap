# SPDX-License-Identifier: AGPL-3.0-or-later
"""Routes du module « Saisons » sous /api/roads (montées seulement si SALUBRI_SEASONS_ENABLED=true)."""

import csv
import io
import json
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from shapely.geometry import shape
from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api.modules.seasons.interface import (
    Commune,
    Report,
    audit,
    get_commune,
    get_session,
    report_tools,
    require_moderateur,
)
from salubri_api.modules.seasons.models import RoadCondition, RoadImportBatch, RoadReport
from salubri_api.modules.seasons.service import load_context

router = APIRouter(prefix="/roads", tags=["Saisons (module)"], dependencies=[Depends(require_moderateur)])
public = APIRouter(prefix="/roads", tags=["Saisons (module)"])  # signalement « Route impraticable » (Salubri Go)

MATCH_M = 15.0  # import : route la plus proche à moins de 15 m quand l'identifiant OSM manque
MAX_IMPORT = 2_000_000
TRUE = {"1", "true", "vrai", "oui", "yes", "o", "praticable", "ouverte"}
FALSE = {"0", "false", "faux", "non", "no", "n", "impraticable", "fermee", "fermée", "coupee", "coupée", "inondee",
         "inondée"}  # fmt: skip
COLUMNS = {  # nom de colonne (minuscules, sans accents ni espaces) → champ
    "osm_id": "osm_id", "osmid": "osm_id", "id_osm": "osm_id", "way_id": "osm_id",
    "lat": "lat", "latitude": "lat", "y": "lat", "lon": "lon", "lng": "lon", "longitude": "lon", "x": "lon",
    "periode": "period", "period": "period", "saison": "period", "season": "period",
    "praticable": "passable", "passable": "passable", "etat": "passable", "statut": "passable",
    "vitesse": "speed_factor", "facteur_vitesse": "speed_factor", "speed_factor": "speed_factor",
    "confiance": "confidence", "confidence": "confidence",
    "date": "observed_at", "observe_le": "observed_at", "observed_at": "observed_at",
    "note": "note", "commentaire": "note", "remarque": "note",
}  # fmt: skip
PERIODS_ALIASES = {"pluie": "rain", "pluies": "rain", "hivernage": "rain", "rain": "rain", "seche": "dry",
                   "sèche": "dry", "dry": "dry", "saison seche": "dry", "saison des pluies": "rain"}  # fmt: skip


def _norm(k: str) -> str:
    import unicodedata

    k = unicodedata.normalize("NFKD", k).encode("ascii", "ignore").decode().strip().lower()
    return k.replace(" ", "_").replace("-", "_")


def _recompute(s: Session, commune_id: uuid.UUID, period: str, why: str) -> int:
    """Recalcule les scénarios de la commune dont la saison est la période modifiée."""
    from salubri_api.models import Scenario
    from salubri_api.services.plan.pipeline import request_recompute

    n = 0
    for sc in s.query(Scenario).filter(Scenario.commune_id == commune_id).all():
        if (sc.params or {}).get("season", "dry") == period:
            request_recompute(s, sc, "season_changed", {"routes": why})
            n += 1
    return n


def _condition_json(c: RoadCondition, osm_id: int | None = None) -> dict[str, Any]:
    return {
        "id": str(c.id), "road_id": str(c.road_id), "osm_id": osm_id, "period": c.period, "passable": c.passable,
        "speed_factor": c.speed_factor, "source": c.source, "confidence": c.confidence,
        "observed_at": c.observed_at.isoformat(), "note": c.note,
        "batch_id": str(c.batch_id) if c.batch_id else None,
    }  # fmt: skip


@router.get("", summary="Routes avec un état pour la période (couche « Routes » de la carte)")
def roads_geojson(
    period: str = "rain", s: Session = Depends(get_session), commune: Commune = Depends(get_commune)
) -> dict[str, Any]:
    ctx = load_context(s, commune.id, period)
    closed = {c.road_id: c.source for c in ctx.closed}
    rows = s.execute(
        text("""SELECT r.id, r.osm_id, r.highway, ST_AsGeoJSON(r.geom) AS g FROM roads r
                WHERE r.commune_id = :c AND (r.id = ANY(:ids) OR r.id IN
                  (SELECT road_id FROM road_conditions WHERE period = :p))"""),
        {"c": commune.id, "ids": list(closed), "p": period},
    ).all()
    slow = {
        c.road_id: c.speed_factor
        for c in s.query(RoadCondition).filter(RoadCondition.period == period, RoadCondition.passable.is_(True))
    }
    return {
        "type": "FeatureCollection",
        "period": period,
        "features": [
            {
                "type": "Feature",
                "geometry": json.loads(r.g),
                "properties": {
                    "road_id": str(r.id),
                    "osm_id": r.osm_id,
                    "highway": r.highway,
                    "passable": r.id not in closed,
                    "source": closed.get(r.id, "manual"),
                    "speed_factor": slow.get(r.id, 0.0 if r.id in closed else 1.0),
                },  # fmt: skip
            }
            for r in rows
        ],
    }


@router.get("/near", summary="Route la plus proche d'un point (choix sur la carte)")
def road_near(
    lon: float, lat: float, s: Session = Depends(get_session), commune: Commune = Depends(get_commune)
) -> dict[str, Any]:
    r = s.execute(
        text("""SELECT id, osm_id, highway, ST_AsGeoJSON(geom) AS g,
                       ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(:x, :y), 4326)::geography) AS d
                FROM roads WHERE commune_id = :c ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:x, :y), 4326) LIMIT 1"""),
        {"x": lon, "y": lat, "c": commune.id},
    ).first()
    if r is None or r.d > 60:
        raise HTTPException(404, "Aucune route à moins de 60 m de ce point")
    return {"road_id": str(r.id), "osm_id": r.osm_id, "highway": r.highway, "distance_m": round(r.d, 1),
            "geometry": json.loads(r.g)}  # fmt: skip


@router.get("/conditions", summary="États des routes saisis, importés ou venus de signalements vérifiés")
def list_conditions(period: str | None = None, s: Session = Depends(get_session)) -> dict[str, Any]:
    q = s.query(RoadCondition)
    if period:
        q = q.filter(RoadCondition.period == period)
    osm = dict(s.execute(text("SELECT id, osm_id FROM roads WHERE id IN (SELECT road_id FROM road_conditions)")).all())
    return {"conditions": [_condition_json(c, osm.get(c.road_id)) for c in q.order_by(RoadCondition.observed_at)]}


class ConditionIn(BaseModel):
    passable: bool
    speed_factor: float = Field(1.0, ge=0, le=1)
    note: str | None = Field(None, max_length=500)


@router.put("/{road_id}/conditions/{period}", summary="Modérateur : route praticable ou non pour une période")
def set_condition(
    road_id: str,
    period: str,
    body: ConditionIn,
    s: Session = Depends(get_session),
    commune: Commune = Depends(get_commune),
) -> dict[str, Any]:
    rid = _uuid(road_id)
    if not s.execute(
        text("SELECT 1 FROM roads WHERE id = :i AND commune_id = :c"), {"i": rid, "c": commune.id}
    ).first():
        raise HTTPException(404, "Route introuvable")
    c = s.query(RoadCondition).filter_by(road_id=rid, period=period[:32], source="manual").first()
    before = _condition_json(c) if c else None
    if c is None:
        c = RoadCondition(road_id=rid, period=period[:32], source="manual")
        s.add(c)
    c.passable, c.speed_factor = body.passable, (0.0 if not body.passable else body.speed_factor)
    c.note, c.confidence, c.observed_at = body.note, 1.0, datetime.now(UTC)
    s.flush()
    audit(s, "update", "road_condition", c.id, before=before, after=_condition_json(c))
    s.commit()
    n = _recompute(s, commune.id, c.period, "modification manuelle")
    return {**_condition_json(c), "scenarios_recalcules": n}


@router.delete("/{road_id}/conditions/{period}", summary="Modérateur : retirer l'état saisi à la main")
def delete_condition(
    road_id: str, period: str, s: Session = Depends(get_session), commune: Commune = Depends(get_commune)
) -> dict[str, Any]:
    c = s.query(RoadCondition).filter_by(road_id=_uuid(road_id), period=period, source="manual").first()
    if c is None:
        raise HTTPException(404, "Pas d'état saisi à la main pour cette route et cette période")
    audit(s, "delete", "road_condition", c.id, before=_condition_json(c))
    s.delete(c)
    s.commit()
    return {"supprime": True, "scenarios_recalcules": _recompute(s, commune.id, period, "état retiré")}


def _rows(name: str, raw: bytes) -> tuple[list[dict[str, Any]], dict[str, str | None]]:
    """Lignes d'un CSV (séparateur deviné) ou d'un GeoJSON, et la correspondance colonne → champ."""
    if name.lower().endswith((".geojson", ".json")) or raw.lstrip()[:1] == b"{":
        try:
            fc = json.loads(raw.decode("utf-8-sig"))
        except ValueError as exc:
            raise HTTPException(422, "GeoJSON illisible") from exc
        rows, cols = [], {}
        for f in fc.get("features", []):
            props = {k: v for k, v in (f.get("properties") or {}).items()}
            g = f.get("geometry")
            if g:
                pt = shape(g).interpolate(0.5, normalized=True) if g["type"] != "Point" else shape(g)
                props["lon"], props["lat"] = pt.x, pt.y
            rows.append(props)
        for r in rows:
            for k in r:
                cols.setdefault(k, COLUMNS.get(_norm(k)) or (k if k in ("lat", "lon") else None))
        return [{cols[k]: v for k, v in r.items() if cols.get(k)} for r in rows], cols
    text_ = raw.decode("utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text_[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rd = csv.DictReader(io.StringIO(text_), dialect=dialect)
    cols = {k: COLUMNS.get(_norm(k)) for k in (rd.fieldnames or [])}
    return [{cols[k]: v for k, v in r.items() if k and cols.get(k)} for r in rd], cols


def _num(v: Any) -> float | None:
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


@router.post("/conditions/import", summary="Importer des états de routes (CSV ou GeoJSON), avec rapport")
def import_conditions(
    file: Annotated[UploadFile, File()],
    dry_run: Annotated[bool, Form()] = False,
    s: Session = Depends(get_session),
    commune: Commune = Depends(get_commune),
) -> dict[str, Any]:
    raw = file.file.read(MAX_IMPORT + 1)
    if len(raw) > MAX_IMPORT:
        raise HTTPException(413, "Fichier trop lourd (2 Mo au plus)")
    rows, cols = _rows(file.filename or "", raw)
    if not any(v in ("osm_id", "lat") for v in cols.values()):
        raise HTTPException(422, "Il faut une colonne d'identifiant OSM (osm_id) ou des coordonnées (lat, lon)")
    batch = RoadImportBatch(commune_id=commune.id, filename=(file.filename or "")[:200], rows=len(rows))
    report: list[dict[str, Any]] = []
    made: list[RoadCondition] = []
    for i, r in enumerate(rows, start=1):
        errs: list[str] = []
        road = None
        osm = _num(r.get("osm_id"))
        if osm is not None:
            road = s.execute(
                text("SELECT id, CAST(0 AS float8) AS d FROM roads WHERE commune_id = :c AND osm_id = :o LIMIT 1"),
                {"c": commune.id, "o": int(osm)},
            ).first()
            if road is None:
                errs.append(f"Route OSM {int(osm)} absente de la carte")
        if road is None and _num(r.get("lat")) is not None and _num(r.get("lon")) is not None:
            road = s.execute(
                text("""SELECT id, ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(:x, :y), 4326)::geography) AS d
                        FROM roads WHERE commune_id = :c
                        ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:x, :y), 4326) LIMIT 1"""),
                {"c": commune.id, "x": _num(r["lon"]), "y": _num(r["lat"])},
            ).first()
            if road is not None and road.d > MATCH_M:
                errs.append(f"Aucune route à moins de {MATCH_M:.0f} m (la plus proche à {road.d:.0f} m)")
                road = None
            else:
                errs = [e for e in errs if not e.startswith("Route OSM")]
        elif road is None and not errs:
            errs.append("Ni identifiant OSM ni coordonnées")
        period = PERIODS_ALIASES.get(_norm(str(r.get("period") or "rain")).replace("_", " "), None)
        if period is None:
            period = str(r.get("period")).strip()[:32] or "rain"
        pv = str(r.get("passable", "")).strip().lower()
        passable = False if pv in FALSE else True if pv in TRUE else None
        if passable is None:
            errs.append(f"État « {r.get('passable')} » illisible (praticable : oui/non)")
        sf = _num(r.get("speed_factor"))
        if sf is not None and not 0 <= sf <= 1:
            errs.append("Facteur de vitesse hors de 0–1")
        when = datetime.now(UTC)
        if r.get("observed_at"):
            try:
                when = datetime.fromisoformat(str(r["observed_at"]).replace("Z", "+00:00"))
                when = when if when.tzinfo else when.replace(tzinfo=UTC)
            except ValueError:
                errs.append("Date illisible (AAAA-MM-JJ)")
        if errs or road is None:
            report.append({"row": i, "status": "rejected", "errors": errs})
            continue
        c = RoadCondition(road_id=road.id, period=period, passable=bool(passable),
                          speed_factor=0.0 if not passable else (sf if sf is not None else 1.0), source="import",
                          confidence=_num(r.get("confidence")) or 0.8, observed_at=when,
                          note=(str(r.get("note")) if r.get("note") else None))  # fmt: skip
        made.append(c)
        report.append({"row": i, "status": "accepted", "road_id": str(road.id), "distance_m": round(float(road.d), 1),
                       "period": period, "passable": bool(passable)})  # fmt: skip
    batch.accepted, batch.report = len(made), report
    out = {"colonnes": cols, "rows": len(rows), "accepted": len(made),
           "rejected": len(rows) - len(made), "report": report, "dry_run": dry_run}  # fmt: skip
    if dry_run:
        s.rollback()
        return out
    s.add(batch)
    s.flush()
    for c in made:  # un import remplace l'état importé précédent de la même route et période
        s.query(RoadCondition).filter_by(road_id=c.road_id, period=c.period, source="import").delete()
        c.batch_id = batch.id
        s.add(c)
    audit(s, "import", "road_conditions", batch.id, after={"fichier": batch.filename, "acceptees": len(made)})
    s.commit()
    n = sum(_recompute(s, commune.id, p, "import") for p in {c.period for c in made})
    return {**out, "batch_id": str(batch.id), "scenarios_recalcules": n}


@router.delete("/conditions/import/{batch_id}", summary="Annuler un import d'états de routes")
def undo_import(batch_id: str, s: Session = Depends(get_session), commune: Commune = Depends(get_commune)) -> dict:  # type: ignore[type-arg]
    b = s.get(RoadImportBatch, _uuid(batch_id))
    if b is None or b.commune_id != commune.id:
        raise HTTPException(404, "Import introuvable")
    if b.undone_at is not None:
        raise HTTPException(409, "Import déjà annulé")
    periods = {c.period for c in s.query(RoadCondition).filter(RoadCondition.batch_id == b.id)}
    n = s.query(RoadCondition).filter(RoadCondition.batch_id == b.id).delete()
    b.undone_at = datetime.now(UTC)
    audit(s, "undo", "road_conditions", b.id, before={"lignes": n})
    s.commit()
    return {
        "supprimees": n,
        "scenarios_recalcules": sum(_recompute(s, commune.id, p, "import annulé") for p in periods),
    }


@router.get("/plans/{plan_id}", summary="Saison d'un plan : points déplacés et inaccessibles, avec les raisons")
def plan_season(plan_id: str, s: Session = Depends(get_session)) -> dict[str, Any]:
    from salubri_api.models import PlanVersion

    pv = s.get(PlanVersion, _uuid(plan_id))
    if pv is None:
        raise HTTPException(404, "Plan introuvable")
    return (pv.summary or {}).get("saisons") or {"periode": (pv.params_snapshot or {}).get("season"),
                                                  "points_deplaces": [], "points_inaccessibles": []}  # fmt: skip


@public.post("/reports", status_code=201, summary="Salubri Go : signaler une route impraticable (photo masquée)")
def road_report(
    lat: Annotated[float, Form()],
    lon: Annotated[float, Form()],
    period: Annotated[str, Form()] = "rain",
    comment: Annotated[str | None, Form()] = None,
    accuracy: Annotated[float | None, Form()] = None,
    device_id: Annotated[str | None, Form()] = None,
    client_id: Annotated[str | None, Form()] = None,
    masking_client: Annotated[str | None, Form()] = None,
    photo: Annotated[UploadFile | None, File()] = None,
    s: Session = Depends(get_session),
    commune: Commune = Depends(get_commune),
) -> dict[str, Any]:
    """Même chemin qu'un signalement de dépotoir (règles, masquage, idempotence par `client_id`), mais toujours
    « à vérifier » : seul un modérateur fait d'un signalement un état de route. Jamais compté comme dépotoir."""
    ReportIn, stage_report, validate_staged = report_tools()
    if client_id:
        ex = s.query(Report).filter(Report.client_id == client_id).first()
        if ex is not None:
            return {"id": str(ex.id), "status": ex.status, "duplicate": True}
    try:
        mc = json.loads(masking_client) if masking_client else None
        data = ReportIn(lat=lat, lon=lon, waste_type="other", volume_class="bag", accuracy=accuracy,
                        comment=("Route impraticable" + (f" : {comment}" if comment else ""))[:1000],
                        device_id=device_id, client_id=client_id, masking_client=mc)  # fmt: skip
    except Exception as exc:
        raise HTTPException(422, "Champs invalides") from exc
    raw = photo.file.read(12 * 1024 * 1024 + 1) if photo is not None else None
    if raw is not None and len(raw) > 12 * 1024 * 1024:
        raise HTTPException(413, "Photo trop lourde (12 Mo maximum)")
    try:
        st = stage_report(s, commune, data, raw or None)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    validate_staged(s, commune, [st])
    rep = st.report
    if rep.status in ("verified", "probable"):  # un modérateur décide
        rep.status = "to_review"
    near = s.execute(
        text("""SELECT id, ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(:x, :y), 4326)::geography) AS d
                FROM roads WHERE commune_id = :c ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:x, :y), 4326) LIMIT 1"""),
        {"c": commune.id, "x": lon, "y": lat},
    ).first()
    s.add(RoadReport(report_id=rep.id, road_id=near.id if near is not None and near.d <= 60 else None,
                     period=PERIODS_ALIASES.get(period.lower(), period[:32]),
                     distance_m=round(near.d, 1) if near is not None else None))  # fmt: skip
    s.commit()
    return {"id": str(rep.id), "status": rep.status, "road_id": str(near.id) if near is not None and near.d <= 60
            else None, "duplicate": False}  # fmt: skip


@public.get("/periodes", summary="Calendrier des périodes de la commune (data/communes/<commune>/saisons.json)")
def periods(commune: Commune = Depends(get_commune)) -> dict[str, Any]:
    from salubri_api.modules.seasons.interface import settings

    f = settings().data_dir / "communes" / commune.slug / "saisons.json"
    if not f.exists():  # commune sans calendrier : les deux saisons du paramètre « season »
        return {"periodes": [{"id": "dry", "libelle": "Saison sèche"}, {"id": "rain", "libelle": "Saison des pluies"}]}
    return {"periodes": json.loads(f.read_text(encoding="utf-8"))["periodes"]}


@router.get("/reports", summary="Signalements « Route impraticable » et leur route")
def list_road_reports(s: Session = Depends(get_session)) -> dict[str, Any]:
    rows = s.execute(
        text("""SELECT rr.report_id, rr.road_id, rr.period, rr.distance_m, r.status, ST_X(r.geom) AS lon,
                       ST_Y(r.geom) AS lat FROM road_reports rr JOIN reports r ON r.id = rr.report_id
                ORDER BY r.received_at DESC LIMIT 500""")
    ).all()
    return {"reports": [{"report_id": str(r.report_id), "road_id": str(r.road_id) if r.road_id else None,
                         "period": r.period, "distance_m": r.distance_m, "status": r.status, "lon": r.lon,
                         "lat": r.lat} for r in rows]}  # fmt: skip


def _uuid(v: str) -> uuid.UUID:
    try:
        return uuid.UUID(v)
    except ValueError as exc:
        raise HTTPException(404, "Identifiant invalide") from exc
