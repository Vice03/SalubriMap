# SPDX-License-Identifier: AGPL-3.0-or-later
"""Module « Saisons » : table vide = rien ne change ; import et annulation ; signalement Go → modération → état ;
saisie du modérateur ; réseau de marche ; pénalité des tournées ; variante saisonnière des points."""

import io
import uuid

import numpy as np
from sqlalchemy import text

from salubri_api.models import PlanVersion, Scenario
from salubri_api.modules.seasons import service
from salubri_api.modules.seasons.models import RoadCondition, RoadReport
from salubri_api.services.plan.pipeline import request_recompute, reset_cache


def _plan(db):  # type: ignore[no-untyped-def]
    pv = request_recompute(db, db.query(Scenario).first(), "manual", sync=True)
    assert pv.status == "ready", pv.error
    pts = db.execute(
        text("SELECT key, ST_X(geom), ST_Y(geom) FROM collection_points WHERE plan_version_id = :p ORDER BY key"),
        {"p": pv.id},
    ).all()
    routes = db.execute(
        text("""SELECT r.rotation, array_agg(cp.key ORDER BY st.seq) FROM routes r
                JOIN route_stops st ON st.route_id = r.id JOIN collection_points cp ON cp.id = st.collection_point_id
                WHERE r.plan_version_id = :p GROUP BY r.id, r.rotation ORDER BY 2"""),
        {"p": pv.id},
    ).all()
    return pv, [tuple(p) for p in pts], [tuple(r) for r in routes]


def _fresh(db) -> None:  # type: ignore[no-untyped-def]
    db.query(PlanVersion).delete()
    db.commit()
    reset_cache()


def test_flag_on_with_empty_table_changes_nothing(db, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from salubri_api.config import get_settings

    monkeypatch.setattr(get_settings(), "deterministic_solvers", True)
    off_pv, off_pts, off_routes = _plan(db)
    _fresh(db)
    monkeypatch.setattr(get_settings(), "seasons_enabled", True)
    on_pv, on_pts, on_routes = _plan(db)
    assert on_pts == off_pts and on_routes == off_routes
    assert on_pv.summary["saisons"]["points_deplaces"] == [] and on_pv.summary["saisons"]["routes_impraticables"] == 0
    assert "saisons" not in off_pv.summary


def _roads(db, n=3):  # type: ignore[no-untyped-def]
    return db.execute(
        text("""SELECT id, osm_id, ST_X(ST_LineInterpolatePoint(geom, 0.5)) AS lon,
                       ST_Y(ST_LineInterpolatePoint(geom, 0.5)) AS lat FROM roads ORDER BY id LIMIT :n"""),
        {"n": n},
    ).all()


def test_routes_are_hidden_when_module_is_off(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/api/roads").status_code == 404
    assert client.get("/api/health").json()["modules"] == {"seasons": False, "assistant": False}


def test_import_with_mapping_report_and_undo(sclient, db) -> None:  # type: ignore[no-untyped-def]
    r1, r2, _ = _roads(db)
    db.execute(text("UPDATE roads SET osm_id = 9001 WHERE id = :i"), {"i": r1.id})
    db.commit()
    csv_ = (
        "OSM ID;Latitude;Longitude;Saison;Praticable;Commentaire\n"
        "9001;;;pluies;non;inondée\n"
        f";{r2.lat};{r2.lon};hivernage;impraticable;\n"
        ";12.0;-1.0;pluie;non;loin de tout\n"
        "9001;;;pluie;peut-être;\n"
    )
    files = {"file": ("routes.csv", io.BytesIO(csv_.encode()), "text/csv")}
    dry = sclient.post("/api/roads/conditions/import", data={"dry_run": "true"}, files=files).json()
    assert dry["accepted"] == 2 and dry["rejected"] == 2 and dry["colonnes"]["Praticable"] == "passable"
    assert db.query(RoadCondition).count() == 0
    files = {"file": ("routes.csv", io.BytesIO(csv_.encode()), "text/csv")}
    body = sclient.post("/api/roads/conditions/import", files=files).json()
    rej = {r["row"]: " ".join(r["errors"]) for r in body["report"] if r["status"] == "rejected"}
    assert "Aucune route à moins de 15 m" in rej[3] and "illisible" in rej[4]
    assert {(c.road_id, c.period, c.passable) for c in db.query(RoadCondition)} == {
        (r1.id, "rain", False), (r2.id, "rain", False)}  # fmt: skip
    ctx = service.load_context(db, db.query(Scenario).first().commune_id, "rain")
    assert {c.road_id for c in ctx.closed} == {r1.id, r2.id}
    assert sclient.delete(f"/api/roads/conditions/import/{body['batch_id']}").json()["supprimees"] == 2
    assert db.query(RoadCondition).count() == 0
    assert sclient.delete(f"/api/roads/conditions/import/{body['batch_id']}").status_code == 409


def test_go_report_goes_through_moderation_then_closes_the_road(sclient, sanon, db, world) -> None:  # type: ignore[no-untyped-def]
    from salubri_api.services.consolidation import consolidate

    (r1,) = _roads(db, 1)
    from salubri_tests_conftest import jpeg

    rep = sanon.post(
        "/api/roads/reports",
        data={"lat": str(r1.lat), "lon": str(r1.lon), "comment": "eau jusqu'aux genoux", "device_id": "dev-r",
              "client_id": "road-1"},
        files={"photo": ("p.jpg", jpeg(41), "image/jpeg")},
    ).json()  # fmt: skip
    assert rep["status"] in ("to_review", "rejected", "pending") and rep["road_id"] == str(r1.id)
    cid = db.query(Scenario).first().commune_id
    assert service.load_context(db, cid, "rain").empty  # pas encore vérifié
    assert sanon.post("/api/roads/reports", data={"lat": str(r1.lat), "lon": str(r1.lon),
                                                  "client_id": "road-1"}).json()["duplicate"]  # fmt: skip
    assert sanon.patch(f"/api/reports/{rep['id']}", json={"status": "verified"}).status_code == 401
    r = sclient.patch(f"/api/reports/{rep['id']}", json={"status": "verified", "reason": "vu sur place"})
    assert r.status_code == 200, r.text
    assert [c.road_id for c in service.load_context(db, cid, "rain").closed] == [r1.id]
    consolidate(db, cid)
    n = db.execute(text("SELECT count(*) FROM reports WHERE dump_site_id IS NOT NULL AND id = :i"),
                   {"i": uuid.UUID(rep["id"])}).scalar()  # fmt: skip
    assert n == 0  # une route impraticable n'est jamais un dépotoir
    assert db.query(RoadReport).count() == 1


def test_moderator_sets_a_road_and_anonymous_cannot(sclient, sanon, db) -> None:  # type: ignore[no-untyped-def]
    (r1,) = _roads(db, 1)
    assert sanon.put(f"/api/roads/{r1.id}/conditions/rain", json={"passable": False}).status_code == 401
    body = sclient.put(f"/api/roads/{r1.id}/conditions/rain", json={"passable": False, "note": "radier"}).json()
    assert body["passable"] is False and body["source"] == "manual" and body["speed_factor"] == 0.0
    near = sclient.get("/api/roads/near", params={"lon": r1.lon, "lat": r1.lat}).json()
    assert near["road_id"] == str(r1.id)
    fc = sclient.get("/api/roads", params={"period": "rain"}).json()
    assert [f["properties"]["passable"] for f in fc["features"]] == [False]
    assert sclient.get("/api/roads", params={"period": "dry"}).json()["features"] == []
    assert sclient.delete(f"/api/roads/{r1.id}/conditions/rain").json()["supprime"]
    assert db.query(RoadCondition).count() == 0


def _ctx_with_line(line_lonlat):  # type: ignore[no-untyped-def]
    from shapely.geometry import LineString

    ctx = service.SeasonContext(uuid.uuid4(), "rain", [service.Closed(uuid.uuid4(), LineString(line_lonlat), 0, "manual")],
                                "x")  # fmt: skip
    service.activate(ctx)
    return ctx


def test_walking_network_excludes_pairs_across_a_closed_road() -> None:
    lat = 12.37
    dlon = 1 / (111_320 * np.cos(np.radians(lat)))  # un mètre en longitude
    ilots = np.array([[-1.52, lat], [-1.52 + 150 * dlon, lat]])
    cand = np.array([[-1.52 + 20 * dlon, lat], [-1.52 + 130 * dlon, lat], [-1.52 + 75 * dlon, lat + 0.0001]])
    _ctx_with_line([(-1.52 + 75 * dlon, lat - 0.002), (-1.52 + 75 * dlon, lat + 0.002)])  # route nord-sud au milieu
    try:
        service.prepare_walk(ilots, cand, 300)
        d = np.full((2, 3), 50.0)
        out = service.apply_walk(d)
        assert out[0, 0] == 50 and out[1, 1] == 50  # même côté : permis
        assert out[0, 1] == service.BLOCKED_M and out[1, 0] == service.BLOCKED_M  # traverse : interdit
        assert (out[:, 2] == service.BLOCKED_M).all()  # site sur la route : inutilisable
        assert service.apply_walk(np.zeros((3, 3))).sum() == 0  # autre placement : inchangé
    finally:
        service.activate(None)


def test_vrp_penalty_on_crossing_arcs_and_unreachable_points() -> None:
    from salubri_api.services.planning.distance import approx_matrix

    lat = 12.37
    nodes = [(-1.520, lat), (-1.515, lat), (-1.510, lat), (-1.520, lat + 0.004)]
    _ctx_with_line([(-1.5125, lat - 0.01), (-1.5125, lat + 0.01)])  # coupe entre les nœuds 1 et 2
    try:
        m = approx_matrix(nodes, "rain")
        p = service.penalise_matrix(m, nodes, {3})
        assert p.distance_km[1, 2] == m.distance_km[1, 2] + service.PENALTY_KM
        assert p.distance_km[0, 1] == m.distance_km[0, 1]
        assert p.distance_km[0, 3] >= service.UNREACHABLE_KM and p.distance_km[3, 0] >= service.UNREACHABLE_KM
        assert m.distance_km[1, 2] < service.PENALTY_KM  # la matrice d'origine n'est pas modifiée
    finally:
        service.activate(None)


def test_rain_moves_points_off_a_closed_access_road_and_dry_restores_them(sclient, db) -> None:  # type: ignore[no-untyped-def]
    sc = db.query(Scenario).first()
    _, dry_pts, _ = _plan(db)
    # route d'accès du premier point qui n'est pas un CCT figé
    key, lon, lat = next(p for p in dry_pts if p[0].startswith("P"))
    road = db.execute(
        text("""SELECT id FROM roads ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:x, :y), 4326) LIMIT 1"""),
        {"x": lon, "y": lat},
    ).scalar()
    assert sclient.put(f"/api/roads/{road}/conditions/rain", json={"passable": False}).status_code == 200
    sc.params = {**sc.params, "season": "rain"}
    db.commit()
    rain = request_recompute(db, sc, "season_changed", sync=True)
    assert rain.status == "ready", rain.error
    sa = rain.summary["saisons"]
    touched = {x["point"] for x in sa["points_deplaces"] + sa["points_inaccessibles"]}
    assert key in touched
    rain_pts = dict(
        (k, (x, y))
        for k, x, y in db.execute(
            text("SELECT key, ST_X(geom), ST_Y(geom) FROM collection_points WHERE plan_version_id = :p"), {"p": rain.id}
        ).all()
    )
    assert set(rain_pts) == {p[0] for p in dry_pts}  # mêmes clés
    for m in sa["points_deplaces"]:
        assert m["distance_m"] > 0 and rain_pts[m["point"]] != next((x, y) for k, x, y in dry_pts if k == m["point"])
    unserved = {r[0] for r in db.execute(text(
        """SELECT cp.key FROM unserved_points u JOIN collection_points cp ON cp.id = u.collection_point_id
           WHERE u.plan_version_id = :p"""), {"p": rain.id}).all()}  # fmt: skip
    assert {x["point"] for x in sa["points_inaccessibles"]} <= unserved  # pas d'arrêt sur une route coupée
    pts = sclient.get(f"/api/roads/plans/{rain.id}").json()
    assert pts["periode"] == "rain"
    sc.params = {**sc.params, "season": "dry"}
    db.commit()
    dry2 = request_recompute(db, sc, "season_changed", sync=True)
    back = sorted(
        tuple(r)
        for r in db.execute(
            text("SELECT key, ST_X(geom), ST_Y(geom) FROM collection_points WHERE plan_version_id = :p"), {"p": dry2.id}
        ).all()
    )
    assert back == sorted(dry_pts)  # retour en saison sèche : chaque position d'origine, exactement


def test_calendar_falls_back_to_dry_and_rain(sanon) -> None:  # type: ignore[no-untyped-def]
    ids = [p["id"] for p in sanon.get("/api/roads/periodes").json()["periodes"]]
    assert ids == ["dry", "rain"]  # testville n'a pas de calendrier : les deux saisons du paramètre
