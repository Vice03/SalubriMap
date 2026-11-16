# SPDX-License-Identifier: AGPL-3.0-or-later
"""Difference between two plan versions, with a one-line French summary for the dashboard."""

from dataclasses import dataclass
from typing import Any

from salubri_api.services.geo import haversine_m


@dataclass
class PlanView:
    points: dict[str, tuple[float, float]]  # key -> (lon, lat)
    routes: set[tuple[str, int, tuple[str, ...]]]  # (vehicle label, rotation, stop keys)
    km: float
    cost: float
    unserved: int


def diff_plans(old: PlanView | None, new: PlanView) -> dict[str, Any]:
    if old is None:
        return {
            "first_version": True,
            "points_added": len(new.points),
            "points_removed": 0,
            "points_moved": 0,
            "routes_changed": len(new.routes),
            "km_delta": round(new.km, 1),
            "km_delta_pct": None,
            "cost_delta": round(new.cost),
            "unserved_delta": new.unserved,
            "text": f"Premier plan : {len(new.points)} points, {len(new.routes)} tournées",
        }
    added = [k for k in new.points if k not in old.points]
    removed = [k for k in old.points if k not in new.points]
    moved = [
        k
        for k in new.points
        if k in old.points and haversine_m(new.points[k][1], new.points[k][0], old.points[k][1], old.points[k][0]) > 5
    ]
    changed = len({r for r in new.routes if r not in old.routes})
    km_delta = new.km - old.km
    pct = (km_delta / old.km * 100) if old.km else None
    parts = []
    if changed:
        parts.append(f"{changed} tournée{'s' if changed > 1 else ''} refaite{'s' if changed > 1 else ''}")
    if added:
        parts.append(f"{len(added)} point{'s' if len(added) > 1 else ''} ajouté{'s' if len(added) > 1 else ''}")
    if moved:
        parts.append(f"{len(moved)} point{'s' if len(moved) > 1 else ''} déplacé{'s' if len(moved) > 1 else ''}")
    if removed:
        parts.append(f"{len(removed)} point{'s' if len(removed) > 1 else ''} supprimé{'s' if len(removed) > 1 else ''}")
    du = new.unserved - old.unserved
    if du:
        parts.append(f"{du:+d} point{'s' if abs(du) > 1 else ''} non desservi{'s' if abs(du) > 1 else ''}")
    if pct is not None and abs(pct) >= 0.5:
        parts.append(f"{pct:+.0f} % de km")
    return {
        "first_version": False,
        "points_added": len(added),
        "points_removed": len(removed),
        "points_moved": len(moved),
        "routes_changed": changed,
        "km_delta": round(km_delta, 1),
        "km_delta_pct": round(pct, 1) if pct is not None else None,
        "cost_delta": round(new.cost - old.cost),
        "unserved_delta": du,
        "text": ", ".join(parts).capitalize() if parts else "Aucun changement",
    }
