# SPDX-License-Identifier: AGPL-3.0-or-later
"""Small geometry helpers shared by services and routers."""

import math
from typing import Any

import numpy as np
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry

EARTH_R_M = 6_371_008.8


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R_M * math.asin(math.sqrt(a))


def haversine_matrix_m(lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """Pairwise great-circle distances in metres (n x n)."""
    la, lo = np.radians(lats)[:, None], np.radians(lons)[:, None]
    dp, dl = la - la.T, lo - lo.T
    a = np.sin(dp / 2) ** 2 + np.cos(la) * np.cos(la.T) * np.sin(dl / 2) ** 2
    return 2 * EARTH_R_M * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def metres_to_deg_lat(m: float) -> float:
    return m / 111_320.0


def metres_to_deg_lon(m: float, lat: float) -> float:
    return m / (111_320.0 * max(math.cos(math.radians(lat)), 1e-6))


def to_wkb(geom: BaseGeometry) -> Any:
    return from_shape(geom, srid=4326)


def shape(geom: Any) -> BaseGeometry:
    return to_shape(geom)


def feature(geom: Any, properties: dict[str, Any], fid: object | None = None) -> dict[str, Any]:
    g = geom if isinstance(geom, BaseGeometry) else to_shape(geom)
    f: dict[str, Any] = {"type": "Feature", "geometry": mapping(g), "properties": properties}
    if fid is not None:
        f["id"] = str(fid)
    return f


def feature_collection(features: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": features, **extra}
