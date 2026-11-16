# SPDX-License-Identifier: AGPL-3.0-or-later
"""Agent state. Households are aggregated per ilot (vectorised); other agents are individual."""

from dataclasses import dataclass, field

import numpy as np


def schedule_days(per_week: float) -> set[int]:
    """Evenly spread `per_week` visits over a 7-day week (0 = Monday)."""
    k = max(0, min(7, round(per_week)))
    return {int(i * 7 / k) for i in range(k)} if k else set()


@dataclass
class TruckRoute:
    vehicle_idx: int
    points: list[int]
    distance_km: float
    capacity_kg: float
    fixed_cost: float


@dataclass
class PlanSnapshot:
    """What the simulator needs from a plan version (built by the pipeline or by tests)."""

    ilot_population: np.ndarray
    ilot_point: np.ndarray  # index of the assigned collection point
    ilot_dist_m: np.ndarray  # walking distance to that point
    ilot_near_water: np.ndarray  # bool
    point_capacity_kg: np.ndarray
    routes: list[TruckRoute]
    unserved_points: set[int] = field(default_factory=set)


@dataclass
class IlotsState:
    population: np.ndarray
    subscribed: np.ndarray
    stock_kg: np.ndarray
    dist_m: np.ndarray
    point: np.ndarray
    passes_planned: np.ndarray
    passes_done: np.ndarray


@dataclass
class Precollector:
    ilots: np.ndarray
    capacity_kg: float
    days: set[int]
    cost_month: float
    active: bool = True
    months_in_loss: int = 0


@dataclass
class WildDumps:
    """Wild dump stocks keyed by location (one per ilot, one per collection point)."""

    kg: np.ndarray
    age: np.ndarray
    near_water: np.ndarray
    cleaned_day: np.ndarray  # last day it was fully cleaned (-1 = never)
    recurring: np.ndarray
