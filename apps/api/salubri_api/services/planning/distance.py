# SPDX-License-Identifier: AGPL-3.0-or-later
"""Distance/duration matrices from OSRM /table, with a haversine fallback that never fails."""

import hashlib
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Literal

import httpx
import numpy as np

from salubri_api.services.geo import haversine_matrix_m

log = logging.getLogger("salubri.distance")

# Facteur de détour du repli sans OSRM (km par route / km à vol d'oiseau), par saison. Valeurs par défaut ;
# celles du scénario viennent de params_default.json (fallback_detour_dry/_rain), calées sur OSRM par
# scripts/calibrer_detour.py (docs/DETOUR_CALIBRATION.md).
DETOUR = {"dry": 1.35, "rain": 1.5}
SPEED_KMH = 25.0
CHUNK = 100


@dataclass
class Matrix:
    distance_km: np.ndarray
    duration_min: np.ndarray
    mode: Literal["osrm", "approx"]
    cache_key: str
    duration_ms: int = 0


_CACHE: "OrderedDict[str, Matrix]" = OrderedDict()
CACHE_MAX_BYTES = 384 * 1024 * 1024


def _cache_bytes() -> int:
    return sum(m.distance_km.nbytes + m.duration_min.nbytes for m in _CACHE.values())


def cache_key(nodes: list[tuple[float, float]], season: str) -> str:
    h = hashlib.sha1(season.encode())
    for lon, lat in nodes:
        h.update(f"{lon:.6f},{lat:.6f};".encode())
    return h.hexdigest()[:16]


def approx_matrix(
    nodes: list[tuple[float, float]], season: str, flood_speed_factor: float = 0.7, detour: float | None = None
) -> Matrix:
    arr = np.array(nodes, dtype=float)
    d_km = haversine_matrix_m(arr[:, 1], arr[:, 0]) / 1000 * (detour or DETOUR.get(season, 1.35))
    speed = SPEED_KMH * (flood_speed_factor if season == "rain" else 1.0)
    return Matrix(d_km, d_km / speed * 60, "approx", cache_key(nodes, season))


def _osrm_table(nodes: list[tuple[float, float]], url: str, timeout: float) -> tuple[np.ndarray, np.ndarray]:
    n = len(nodes)
    coords = ";".join(f"{lon:.6f},{lat:.6f}" for lon, lat in nodes)
    dist = np.zeros((n, n))
    dur = np.zeros((n, n))
    with httpx.Client(timeout=timeout) as client:
        for s0 in range(0, n, CHUNK):
            for d0 in range(0, n, CHUNK):
                src = ";".join(str(i) for i in range(s0, min(n, s0 + CHUNK)))
                dst = ";".join(str(i) for i in range(d0, min(n, d0 + CHUNK)))
                r = client.get(
                    f"{url}/table/v1/driving/{coords}",
                    params={"annotations": "distance,duration", "sources": src, "destinations": dst},
                )
                r.raise_for_status()
                body = r.json()
                if body.get("code") != "Ok":
                    raise RuntimeError(body.get("message", "OSRM error"))
                dd = np.array(body["distances"], dtype=float)
                tt = np.array(body["durations"], dtype=float)
                dist[s0 : s0 + dd.shape[0], d0 : d0 + dd.shape[1]] = dd
                dur[s0 : s0 + tt.shape[0], d0 : d0 + tt.shape[1]] = tt
    if np.isnan(dist).any():
        raise RuntimeError("OSRM: nœuds non reliés au réseau")
    return dist / 1000, dur / 60


def build_matrix(
    nodes: list[tuple[float, float]],
    season: str,
    osrm_url: str | None,
    timeout: float = 1.5,
    flood_speed_factor: float = 0.7,
    detour: float | None = None,
) -> Matrix:
    key = cache_key(nodes, season) + ("|" + osrm_url if osrm_url else "")
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return _CACHE[key]
    t0 = time.perf_counter()
    m: Matrix
    if osrm_url:
        try:
            d, t = _osrm_table(nodes, osrm_url, timeout)
            m = Matrix(d, t, "osrm", cache_key(nodes, season))
        except Exception as exc:  # network, timeout, bad graph: never fail the plan
            log.warning("OSRM indisponible (%s), repli haversine", exc)
            m = approx_matrix(nodes, season, flood_speed_factor, detour)
    else:
        m = approx_matrix(nodes, season, flood_speed_factor, detour)
    m.duration_ms = int((time.perf_counter() - t0) * 1000)
    if m.mode == "osrm":
        _CACHE[key] = m
        # borne par nombre ET par taille : une matrice de la ville entière (2 000 nœuds) pèse ~64 Mo
        while len(_CACHE) > 32 or (len(_CACHE) > 1 and _cache_bytes() > CACHE_MAX_BYTES):
            _CACHE.popitem(last=False)
    return m


def route_geometry(
    stops: list[tuple[float, float]], osrm_url: str | None, timeout: float = 1.5
) -> list[tuple[float, float]]:
    """Road geometry of a tour from OSRM, or straight segments when OSRM is not available."""
    if osrm_url and len(stops) >= 2:
        try:
            coords = ";".join(f"{lon:.6f},{lat:.6f}" for lon, lat in stops)
            r = httpx.get(
                f"{osrm_url}/route/v1/driving/{coords}",
                params={"overview": "simplified", "geometries": "geojson"},
                timeout=timeout,
            )
            r.raise_for_status()
            body = r.json()
            if body.get("code") == "Ok":
                return [tuple(c) for c in body["routes"][0]["geometry"]["coordinates"]]  # type: ignore[misc]
        except Exception as exc:
            log.info("Tracé OSRM indisponible (%s)", exc)
    return stops
