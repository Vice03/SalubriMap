# SPDX-License-Identifier: AGPL-3.0-or-later
"""Logique du module « Saisons ». Approximations volontairement simples et explicables (docs/HYPOTHESES.md) :

- une route impraticable est un couloir de `BUFFER_M` mètres qu'on ne traverse pas à pied ni en camion ;
- marche : une paire (îlot, site) dont le segment à vol d'oiseau traverse ce couloir est interdite au placement,
  un site dans le couloir n'est pas utilisable (le ménage passe à un autre point ou perd la couverture) ;
- point existant dont la route d'accès devient impraticable : déplacé vers le site praticable le plus proche qui
  garde à portée de marche tous les ménages qu'il servait à portée, même clé ; sinon laissé et signalé ;
- tournées : un arc qui traverse un couloir coûte `PENALTY_KM` de plus (prohibitif) ; un point inaccessible n'est
  plus desservi (arcs hors de prix : abandonné par le solveur) ;
- une route sans ligne dans `road_conditions` garde le comportement d'avant (étiquette `surface`, détour par saison).
"""

import hashlib
import math
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any

import numpy as np
from shapely import wkb
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api.modules.seasons.models import RoadCondition, RoadReport

BUFFER_M = 10.0  # demi-largeur du couloir infranchissable autour d'une route impraticable
ACCESS_M = 30.0  # route d'accès d'un point : la route la plus proche à moins de 30 m
SITE_CLEAR_M = 15.0  # un site candidat à moins de 15 m d'une route impraticable n'est pas utilisable
PENALTY_KM = 50.0  # arc qui traverse une route impraticable : prohibitif devant un arc de 1 à 5 km en ville
PENALTY_MIN = 120.0
UNREACHABLE_KM = 100_000.0  # point inaccessible : plus cher que l'abandon du point dans le VRP
BLOCKED_M = 1e6  # distance de marche d'une paire interdite (hors de tout rayon de recherche)
DETOUR = 1.2  # même détour de marche que le placement et la simulation
M_PER_DEG = 111_320.0


@dataclass
class Closed:
    road_id: uuid.UUID
    line: LineString  # lon/lat
    speed_factor: float
    source: str


@dataclass
class SeasonContext:
    commune_id: uuid.UUID
    period: str
    closed: list[Closed]
    signature: str
    walk: dict[str, Any] = field(default_factory=dict)  # masque de marche préparé pour le placement en cours

    @property
    def empty(self) -> bool:
        return not self.closed


_ctx: ContextVar[SeasonContext | None] = ContextVar("salubri_seasons_ctx", default=None)


def current() -> SeasonContext | None:
    return _ctx.get()


def activate(ctx: SeasonContext | None) -> None:
    _ctx.set(ctx)


def period_of(season: str) -> str:
    return season or "dry"


# ---------------------------------------------------------------- lecture de l'état des routes
def load_context(s: Session, commune_id: uuid.UUID, period: str) -> SeasonContext:
    """Routes impraticables pour la période : dernier état connu de chaque route (manuel > signalement > import à
    date égale), plus les signalements « Route impraticable » vérifiés."""
    rank = {"manual": 3, "report": 2, "import": 1}
    best: dict[uuid.UUID, RoadCondition] = {}
    rows = (
        s.query(RoadCondition)
        .filter(RoadCondition.period == period)
        .filter(text("EXISTS (SELECT 1 FROM roads r WHERE r.id = road_conditions.road_id AND r.commune_id = :c)"))
        .params(c=commune_id)
        .all()
    )
    for r in rows:
        cur = best.get(r.road_id)
        key = (r.observed_at, rank.get(r.source, 0))
        if cur is None or key > (cur.observed_at, rank.get(cur.source, 0)):
            best[r.road_id] = r
    closed_src: dict[uuid.UUID, tuple[float, str]] = {
        rid: (c.speed_factor, c.source) for rid, c in best.items() if not c.passable
    }
    for rr in (
        s.query(RoadReport)
        .filter(RoadReport.period == period, RoadReport.road_id.isnot(None))
        .filter(text("EXISTS (SELECT 1 FROM reports r WHERE r.id = road_reports.report_id AND r.status = 'verified')"))
        .all()
    ):
        if rr.road_id not in best:  # un état saisi à la main ou importé plus tard l'emporte
            closed_src[rr.road_id] = (0.0, "report")  # type: ignore[index]
    closed: list[Closed] = []
    if closed_src:
        geoms = s.execute(
            text("SELECT id, ST_AsBinary(geom) AS g FROM roads WHERE id = ANY(:ids)"), {"ids": list(closed_src)}
        ).all()
        for g in sorted(geoms, key=lambda r: str(r.id)):
            sf, src = closed_src[g.id]
            closed.append(Closed(g.id, wkb.loads(bytes(g.g)), sf, src))
    sig = hashlib.sha1(f"{period}|".encode() + "|".join(str(c.road_id) for c in closed).encode()).hexdigest()[:16]
    return SeasonContext(commune_id, period, closed, sig)


# ---------------------------------------------------------------- géométrie locale (mètres)
def _local(lat0: float):  # type: ignore[no-untyped-def]
    kx = M_PER_DEG * math.cos(math.radians(lat0))

    def xy(lon: float, lat: float) -> tuple[float, float]:
        return lon * kx, lat * M_PER_DEG

    return xy, kx


def _corridor(ctx: SeasonContext, xy, pad_m: float):  # type: ignore[no-untyped-def]
    if ctx.empty:
        return None
    lines = [LineString([xy(x, y) for x, y in c.line.coords]) for c in ctx.closed]
    return unary_union([ln.buffer(pad_m) for ln in lines])


def _crossing_mask(a_xy: np.ndarray, b_xy: np.ndarray, pairs: np.ndarray, zone: Any) -> np.ndarray:
    """Pour chaque paire (i, j) de `pairs`, le segment a_i → b_j traverse-t-il `zone` ?"""
    import shapely

    if zone is None or not len(pairs):
        return np.zeros(len(pairs), dtype=bool)
    segs = shapely.linestrings(np.stack([a_xy[pairs[:, 0]], b_xy[pairs[:, 1]]], axis=1))
    shapely.prepare(zone)
    return shapely.intersects(segs, zone)


# ---------------------------------------------------------------- A2 : réseau de marche du placement
def prepare_walk(lonlat_ilots: np.ndarray, cand_lonlat: np.ndarray, walk_max: float) -> None:
    """Appelé par le placement (module allumé) : calcule les paires îlot-site interdites pour la période."""
    ctx = current()
    if ctx is None or ctx.empty or not len(lonlat_ilots) or not len(cand_lonlat):
        if ctx is not None:
            ctx.walk = {}
        return
    xy, _ = _local(float(lonlat_ilots[:, 1].mean()))
    a = np.array([xy(*p) for p in lonlat_ilots])
    b = np.array([xy(*p) for p in cand_lonlat])
    d = np.hypot(a[:, None, 0] - b[None, :, 0], a[:, None, 1] - b[None, :, 1]) * DETOUR
    pairs = np.argwhere(d <= 1.5 * walk_max)
    blocked = np.zeros(d.shape, dtype=bool)
    blocked[pairs[:, 0], pairs[:, 1]] = _crossing_mask(a, b, pairs, _corridor(ctx, xy, BUFFER_M))
    site = _corridor(ctx, xy, SITE_CLEAR_M)
    import shapely

    shapely.prepare(site)
    bad_site = shapely.intersects(shapely.points(b), site)
    blocked[:, bad_site] = True
    ctx.walk = {"shape": d.shape, "blocked": blocked, "sites_exclus": int(bad_site.sum()),
                "paires_coupees": int(blocked.sum())}  # fmt: skip


def apply_walk(d: np.ndarray) -> np.ndarray:
    """Appelé par l'optimiseur (module allumé) : distances des paires interdites portées hors de tout rayon."""
    ctx = current()
    if ctx is None or not ctx.walk or ctx.walk.get("shape") != d.shape:
        return d
    out = d.copy()
    out[ctx.walk["blocked"]] = BLOCKED_M
    return out


# ---------------------------------------------------------------- A3 : variante saisonnière des points
@dataclass
class Variant:
    moved: list[dict[str, Any]]
    inaccessible: list[dict[str, Any]]


def _access_roads(s: Session, commune_id: uuid.UUID, pts: list[tuple[float, float]]) -> list[uuid.UUID | None]:
    if not pts:
        return []
    rows = s.execute(
        text("""
        SELECT u.i, (SELECT r.id FROM roads r WHERE r.commune_id = :c
                       AND ST_DWithin(r.geom::geography, u.g::geography, :m)
                     ORDER BY r.geom <-> u.g LIMIT 1) AS rid
        FROM (SELECT i, ST_SetSRID(ST_MakePoint(lon, lat), 4326) AS g
              FROM unnest(CAST(:lons AS float8[]), CAST(:lats AS float8[])) WITH ORDINALITY AS t(lon, lat, i)) u
        ORDER BY u.i"""),
        {"lons": [p[0] for p in pts], "lats": [p[1] for p in pts], "c": commune_id, "m": ACCESS_M},
    ).all()
    return [r.rid for r in rows]


def seasonal_variant(
    s: Session,
    placement: Any,
    ilot_lonlat: np.ndarray,
    ilot_population: np.ndarray,
    candidates: Any,
    walk_max: float,
    household_size: float = 7.0,
) -> tuple[Any, Variant]:
    """Points dont la route d'accès est impraticable pour la période : déplacés (même clé) ou signalés.

    Ne modifie pas `placement` (il peut venir du cache) : renvoie une copie. Sans route impraticable : inchangé."""
    ctx = current()
    if ctx is None or ctx.empty or not placement.points:
        return placement, Variant([], [])
    closed_ids = {c.road_id for c in ctx.closed}
    access = _access_roads(s, ctx.commune_id, [(p.lon, p.lat) for p in placement.points])
    todo = [k for k, rid in enumerate(access) if rid in closed_ids]
    if not todo:
        return placement, Variant([], [])
    xy, _ = _local(float(ilot_lonlat[:, 1].mean()))
    zone = _corridor(ctx, xy, BUFFER_M)
    site_zone = _corridor(ctx, xy, SITE_CLEAR_M)
    pts = [replace(p) for p in placement.points]
    moved, inacc = [], []
    for k in todo:
        p = pts[k]
        il = np.flatnonzero(placement.assignment == k)
        il_xy = np.array([xy(*ilot_lonlat[i]) for i in il]) if len(il) else np.zeros((0, 2))
        p_xy = np.array(xy(p.lon, p.lat))
        d0 = np.hypot(*(il_xy - p_xy).T) * DETOUR if len(il) else np.zeros(0)
        keep = d0 <= walk_max  # ménages qu'il servait à portée : ils doivent le rester
        pad = walk_max / M_PER_DEG * 1.5
        cand = candidates((p.lon - pad, p.lat - pad, p.lon + pad, p.lat + pad)) or []
        best = None
        if getattr(p, "frozen", False):  # CCT existant : un site bâti ne se déplace pas, il est signalé
            cand = []
        for lon, lat in sorted(cand, key=lambda c: (c[0] - p.lon) ** 2 + (c[1] - p.lat) ** 2):
            c_xy = np.array(xy(lon, lat))
            if site_zone is not None and site_zone.contains(Point(c_xy)):
                continue
            if len(il):
                dc = np.hypot(*(il_xy - c_xy).T) * DETOUR
                if (dc[keep] > walk_max).any():
                    continue
                segs = np.array([[i, 0] for i in np.flatnonzero(keep)])
                if len(segs) and _crossing_mask(il_xy, c_xy[None, :], segs, zone).any():
                    continue
            best = (lon, lat, float(np.hypot(*(c_xy - p_xy))))
            break
        hh = int(round(float(ilot_population[il].sum()) / household_size)) if len(il) else 0
        if best is not None:
            p.lon, p.lat = best[0], best[1]
            moved.append({"point": p.key, "distance_m": round(best[2]), "raison": "route d'accès impraticable",
                          "route": str(access[k]), "menages": hh})  # fmt: skip
        else:
            why = "inaccessible en saison des pluies" if ctx.period == "rain" else f"inaccessible ({ctx.period})"
            if getattr(p, "frozen", False):
                why += " (CCT existant, non déplacé)"
            inacc.append({"point": p.key, "raison": why, "route": str(access[k]), "menages": hh,
                          "population": round(float(ilot_population[il].sum()))})  # fmt: skip
    new = replace(placement, points=pts)
    return new, Variant(moved, inacc)


# ---------------------------------------------------------------- A4 : tournées
def penalise_matrix(matrix: Any, nodes: list[tuple[float, float]], inaccessible: set[int]) -> Any:
    """Copie de la matrice : arcs qui traversent une route impraticable hors de prix, points inaccessibles
    (indices de nœuds) abandonnés. Sans route impraticable : la même matrice."""
    ctx = current()
    if ctx is None or ctx.empty:
        return matrix
    xy, _ = _local(float(np.mean([n[1] for n in nodes])))
    a = np.array([xy(*n) for n in nodes])
    n = len(nodes)
    pairs = np.array([(i, j) for i in range(n) for j in range(n) if i != j])
    cross = _crossing_mask(a, a, pairs, _corridor(ctx, xy, BUFFER_M)) if len(pairs) else np.zeros(0, bool)
    dist = matrix.distance_km.copy()
    dur = matrix.duration_min.copy()
    if cross.any():
        ij = pairs[cross]
        dist[ij[:, 0], ij[:, 1]] += PENALTY_KM
        dur[ij[:, 0], ij[:, 1]] += PENALTY_MIN
    for k in inaccessible:
        dist[k, :] += UNREACHABLE_KM
        dist[:, k] += UNREACHABLE_KM
        dist[k, k] = 0
    return replace(matrix, distance_km=dist, duration_min=dur)


# ---------------------------------------------------------------- A5 : simulation
def adjust_snapshot(
    snap: Any, ilot_lonlat: np.ndarray, pts_lonlat: list[tuple[float, float]], inacc_idx: set[int]
) -> Any:
    """Ménages d'un point inaccessible : point accessible le plus proche (la règle de choix existante décide
    ensuite s'ils y vont ou jettent selon la distance). Aucun nouveau paramètre de comportement."""
    if not inacc_idx or not len(ilot_lonlat):
        return snap
    ok = [k for k in range(len(pts_lonlat)) if k not in inacc_idx]
    if not ok:
        return snap
    xy, _ = _local(float(ilot_lonlat[:, 1].mean()))
    a = np.array([xy(*p) for p in ilot_lonlat])
    b = np.array([xy(*pts_lonlat[k]) for k in ok])
    point = snap.ilot_point.copy()
    dist = snap.ilot_dist_m.copy()
    for i in np.flatnonzero(np.isin(point, list(inacc_idx))):
        d = np.hypot(*(b - a[i]).T) * DETOUR
        j = int(d.argmin())
        point[i], dist[i] = ok[j], float(d[j])
    return replace(snap, ilot_point=point, ilot_dist_m=dist)


def summary(ctx: SeasonContext, variant: Variant, routes_crossing: int | None = None) -> dict[str, Any]:
    return {
        "periode": ctx.period,
        "routes_impraticables": len(ctx.closed),
        "points_deplaces": variant.moved,
        "points_inaccessibles": variant.inaccessible,
        "paires_marche_coupees": ctx.walk.get("paires_coupees", 0) if ctx.walk else 0,
        "sites_exclus": ctx.walk.get("sites_exclus", 0) if ctx.walk else 0,
    }


def now() -> datetime:
    from datetime import UTC

    return datetime.now(UTC)
