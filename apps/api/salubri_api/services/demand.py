# SPDX-License-Identifier: AGPL-3.0-or-later
"""Ilots (blocks of ~30 buildings) and daily waste demand. Pure functions, no database access."""

import math
from dataclasses import dataclass, field

import numpy as np
from shapely.geometry import MultiPoint, Point, Polygon
from shapely.geometry.base import BaseGeometry
from sklearn.cluster import MiniBatchKMeans

from salubri_api.services.geo import metres_to_deg_lat, metres_to_deg_lon
from salubri_api.services.params import ScenarioParams


@dataclass
class IlotDraft:
    quartier_id: str
    lon: float
    lat: float
    polygon: Polygon
    n_buildings: int
    population: float
    building_idx: list[int] = field(default_factory=list)


def build_ilots(
    quartier_id: str,
    quartier_geom: BaseGeometry,
    population: float,
    buildings: list[tuple[float, float, float]],
    target_size: int = 30,
    seed: int = 42,
) -> list[IlotDraft]:
    """buildings: (lon, lat, area_m2) inside the quartier. Without buildings, a 250 m grid carries the population."""
    if not buildings:
        return grid_ilots(quartier_id, quartier_geom, population)
    xy = np.array([[b[0], b[1]] for b in buildings])
    area = np.array([max(b[2], 1.0) for b in buildings])
    k = max(1, min(len(buildings), round(len(buildings) / target_size)))
    if k == 1:
        labels = np.zeros(len(buildings), dtype=int)
    else:
        km = MiniBatchKMeans(n_clusters=k, random_state=seed, n_init=3, batch_size=2048)
        labels = km.fit_predict(xy)
    total_area = float(area.sum())
    out: list[IlotDraft] = []
    for lab in np.unique(labels):
        idx = np.where(labels == lab)[0]
        pts = MultiPoint([tuple(p) for p in xy[idx]])
        lat0 = float(xy[idx, 1].mean())
        poly = pts.convex_hull.buffer(metres_to_deg_lon(5, lat0))
        if not isinstance(poly, Polygon):
            poly = Point(xy[idx, 0].mean(), lat0).buffer(metres_to_deg_lat(10))
        pop = population * float(area[idx].sum()) / total_area
        out.append(IlotDraft(quartier_id, float(xy[idx, 0].mean()), lat0, poly, len(idx), pop, idx.tolist()))
    return out


def grid_ilots(quartier_id: str, geom: BaseGeometry, population: float, step_m: float = 250) -> list[IlotDraft]:
    minx, miny, maxx, maxy = geom.bounds
    lat0 = (miny + maxy) / 2
    dx, dy = metres_to_deg_lon(step_m, lat0), metres_to_deg_lat(step_m)
    cells: list[Polygon] = []
    y = miny
    while y < maxy:
        x = minx
        while x < maxx:
            cell = Polygon([(x, y), (x + dx, y), (x + dx, y + dy), (x, y + dy)]).intersection(geom)
            if not cell.is_empty and cell.area > 0 and isinstance(cell, Polygon):
                cells.append(cell)
            x += dx
        y += dy
    if not cells:
        c = geom.representative_point()
        cells = [Point(c.x, c.y).buffer(metres_to_deg_lat(50))]  # type: ignore[list-item]
    tot = sum(c.area for c in cells)
    return [IlotDraft(quartier_id, c.centroid.x, c.centroid.y, c, 0, population * c.area / tot) for c in cells]


def demand_kg_day(population: np.ndarray, p: ScenarioParams) -> np.ndarray:
    rain = 0.15 if p.season == "rain" else 0.0
    return population * p.population_factor * p.waste_kg_per_person_day * (1 + rain)


def weekly_tonnes(kg_day: np.ndarray) -> float:
    return float(kg_day.sum()) * 7 / 1000


def k_initial(total_t_week: float, p: ScenarioParams) -> int:
    per_point_week = p.collection_point_capacity_t * p.pickup_frequency_per_week
    return max(1, min(p.collection_point_max, math.ceil(total_t_week / per_point_week)))
