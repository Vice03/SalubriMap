#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Banc d'essai des tournées (VRP) : écart à la meilleure solution connue et à une borne inférieure.

    PYTHONPATH=apps/api python scripts/benchmark_tournees.py

Instances : dernier plan prêt des scénarios « Zone pilote » (un arrondissement de démo) et « Ville entière (démo) ».
Matrice approchée (vol d'oiseau × détour, comme sans OSRM) pour que le banc soit reproductible. Pour chaque
instance : 3 stratégies de départ × limites 1, 5 et 15 s. Meilleure connue = meilleur objectif de toutes ces
exécutions. Écrit docs/BENCHMARK_TOURNEES.md.
"""

import re
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
from shapely import wkb

from salubri_api.db import get_sessionmaker
from salubri_api.models import CollectionPoint, Commune, PlanVersion, Scenario, Vehicle
from salubri_api.services.params import ScenarioParams
from salubri_api.services.planning.distance import approx_matrix
from salubri_api.services.planning.vrp import (
    STRATEGIES,
    VehicleSpec,
    effective_time_limit,
    lower_bound_km,
    solve_vrp,
)

ROOT = Path(__file__).resolve().parents[1]
INSTANCES = ["Zone pilote", "Ville entière (démo)"]
LIMITS = [1, 5, 15]


def instance(s, name):  # type: ignore[no-untyped-def]
    sc = s.query(Scenario).filter(Scenario.name == name).first()
    pv = (
        s.query(PlanVersion)
        .filter(PlanVersion.scenario_id == sc.id, PlanVersion.status == "ready")
        .order_by(PlanVersion.version.desc())
        .first()
    )
    params = ScenarioParams(**(pv.params_snapshot or {}))
    commune = s.get(Commune, sc.commune_id)
    depot = wkb.loads(bytes(commune.depot_geom.data))
    pts = s.query(CollectionPoint).filter(CollectionPoint.plan_version_id == pv.id).order_by(CollectionPoint.idx).all()
    nodes = [(depot.x, depot.y)] + [(wkb.loads(bytes(p.geom.data)).x, wkb.loads(bytes(p.geom.data)).y) for p in pts]
    per_pickup = np.minimum(np.array([p.demand_t_week for p in pts]) / params.pickup_frequency_per_week,
                            np.array([p.capacity_t for p in pts]))  # fmt: skip
    vehicles = (
        s.query(Vehicle)
        .filter(Vehicle.scenario_id == sc.id, Vehicle.out_of_service.is_(False), Vehicle.retired.is_(False))
        .order_by(Vehicle.label)
        .all()
    )
    specs = [
        VehicleSpec(v.capacity_t, v.cost_per_km, v.fixed_cost_day, v.shift_start, v.shift_end, v.label)
        for v in vehicles
    ]
    tws = [(0, 1440)] + [(p.tw_start, p.tw_end) for p in pts]
    m = approx_matrix(nodes, params.season, params.flood_speed_factor)
    return f"{name} (plan v{pv.version})", m, np.concatenate([[0.0], per_pickup]), specs, tws


def main() -> int:
    rows = []
    with get_sessionmaker()() as s:
        insts = [instance(s, n) for n in INSTANCES]
    for label, m, dem, specs, tws in insts:
        runs = []
        for lim in LIMITS:
            for strat in STRATEGIES:
                t0 = time.perf_counter()
                sol = solve_vrp(
                    m.distance_km, m.duration_min, dem, specs, tws, 10, time_limit_s=lim, first_solution=strat
                )
                km = sum(r.distance_km for r in sol.routes)
                served = sorted({x for r in sol.routes for x in r.stops})
                runs.append(
                    (lim, strat, sol.objective, km, len(sol.unserved), time.perf_counter() - t0, served, sol.solver)
                )
                print(label, lim, strat, round(sol.objective), round(km, 1), len(sol.unserved), flush=True)
        valid = [r for r in runs if r[7] == "ortools"]
        best = min(r[2] for r in valid) if valid else min(r[2] for r in runs)
        cap = max(v.capacity_t for v in specs)
        rows.append((label, len(dem) - 1, len(specs), runs, best, cap, m, dem))
    out = [
        "<!-- SPDX-License-Identifier: CC-BY-4.0 -->",
        "# Banc d'essai des tournées",
        "",
        f"Généré par `scripts/benchmark_tournees.py` le {date.today().isoformat()} (2 cœurs, matrice approchée "
        "vol d'oiseau × détour). Objectif OR-Tools = coût (carburant au km + coût fixe des camions sortis + "
        "pénalité par point non desservi). **Écart** = écart à la meilleure solution connue (meilleur objectif "
        "des 9 exécutions de l'instance) ; **borne** = borne inférieure garantie des km "
        "(`vrp.lower_bound_km` : radiale et aller-retour le plus long), faible, donc l'écart aux km qu'elle donne "
        "est un majorant très prudent.",
        "",
    ]
    for label, npts, nveh, runs, best, cap, m, dem in rows:
        out += [
            f"## {label} — {npts} points, {nveh} camions",
            "",
            "| Limite (effective) | Départ | Objectif | Écart à la meilleure connue | km | Borne inf. km "
            "| Desservis | Durée |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for lim, strat, obj, km, unserved, dur, served, solver in runs:
            lb = lower_bound_km(m.distance_km, dem, served, cap)
            eff = effective_time_limit(lim, len(dem))
            if solver == "ortools":
                gap = f"{100 * (obj - best) / best:.1f} %"
            else:  # heuristique de repli : objectif sans pénalités, pas comparable
                gap, strat = "— (repli)", f"{strat} → heuristique de repli"
            out.append(
                f"| {lim} s ({eff:g} s) | {strat} | {obj:,.0f} | {gap} | {km:.1f} | {lb:.1f} "
                f"| {npts - unserved} / {npts} | {dur:.1f} s |".replace(",", " ")
            )
        out.append("")
    pilot, city = rows[0], rows[-1]
    gap1 = min(100 * (r[2] - pilot[4]) / pilot[4] for r in pilot[3] if r[0] == 1 and r[7] == "ortools")
    served_best = max(city[1] - r[4] for r in city[3])
    out += [
        "## Lecture",
        "",
        f"- **Zone pilote** : à 1 s, la meilleure stratégie est à {gap1:.1f} % de la meilleure solution connue.",
        f"- **Ville entière (démo)** : la flotte de démonstration ({city[2]} camions) ne dessert que "
        f"{served_best} points sur {city[1]} par jour d'enlèvement ; l'objectif est dominé par la pénalité des points "
        "non desservis. Ce n'est pas un défaut du solveur : il manque des camions (ou des rotations) pour la ville. "
        "À reprendre avec la vraie flotte de la mairie.",
        "- La limite par défaut du test en direct est 1 s (`vrp_time_limit_s`), relevée automatiquement pour les "
        "grandes instances (1 s par 300 points, au plus 8 s).",
        "- L'écart de 1 s à la meilleure connue mesure ce que coûte la réponse rapide pendant la démonstration ; "
        "relancer avec une limite plus longue pour le plan définitif.",
        "",
    ]
    text = re.sub(r"(\d)\.(\d) %", r"\1,\2 %", "\n".join(out))  # décimales à la française
    (ROOT / "docs/BENCHMARK_TOURNEES.md").write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
