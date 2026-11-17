# SPDX-License-Identifier: AGPL-3.0-or-later
"""Difference between two plan versions, with a one-line French summary for the dashboard."""

from dataclasses import dataclass
from typing import Any

import numpy as np

from salubri_api.services.geo import haversine_m


@dataclass
class PlanView:
    points: dict[str, tuple[float, float]]  # key -> (lon, lat)
    routes: set[tuple[str, int, tuple[str, ...]]]  # (vehicle label, rotation, stop keys)
    km: float
    cost: float
    unserved: int
    coverage: float | None = None  # part de la population à distance de marche de son point


def coherence(old: PlanView, new: PlanView, moved_m: float = 5.0) -> dict[str, Any]:
    """Cohérence d'une version avec la précédente : ce qui n'a pas bougé, de combien le reste a bougé, et si les
    camions servent encore les mêmes points."""
    same = [
        k
        for k in old.points
        if k in new.points
        and haversine_m(new.points[k][1], new.points[k][0], old.points[k][1], old.points[k][0]) <= moved_m
    ]
    disp = []
    new_ll = np.array(list(new.points.values())) if new.points else np.zeros((0, 2))
    for k, (lon, lat) in old.points.items():
        if k in same:
            continue
        if k in new.points:  # même point, déplacé
            disp.append(haversine_m(lat, lon, new.points[k][1], new.points[k][0]))
        elif len(new_ll):  # supprimé : remplacé par le point le plus proche du nouveau plan
            disp.append(min(haversine_m(lat, lon, b, a) for a, b in new_ll))
    pairs_old = {(v, s) for v, _r, stops in old.routes for s in stops}
    pairs_new = {(v, s) for v, _r, stops in new.routes for s in stops}
    union = pairs_old | pairs_new
    return {
        "points_inchanges_part": round(len(same) / len(old.points), 3) if old.points else None,
        "deplacement_moyen_m": round(float(np.mean(disp)), 1) if disp else 0.0,
        "deplacement_max_m": round(float(np.max(disp)), 1) if disp else 0.0,
        "tournees_jaccard": round(len(pairs_old & pairs_new) / len(union), 3) if union else 1.0,
        "cout_delta": round(new.cost - old.cost),
        "km_delta": round(new.km - old.km, 1),
        "couverture_avant": old.coverage,
        "couverture_apres": new.coverage,
    }


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
            "coherence": None,
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
        "coherence": coherence(old, new),
        "text": ", ".join(parts).capitalize() if parts else "Aucun changement",
    }
