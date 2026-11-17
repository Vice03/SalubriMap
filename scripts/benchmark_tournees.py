#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Banc d'essai des tournées (VRP) : écart à la meilleure solution connue et à une borne inférieure.

    PYTHONPATH=apps/api python scripts/benchmark_tournees.py [--osrm http://localhost:5000]

Instances : dernier plan prêt des scénarios « Zone pilote » (un arrondissement de démo) et « Ville entière (démo) ».
Pour chaque instance : OR-Tools (3 stratégies de départ × limites 1, 5 et 15 s) et l'heuristique de repli
(économies de Clarke-Wright + 2-opt, utilisée quand OR-Tools ne trouve rien), sur la matrice approchée
(vol d'oiseau × détour, comme sans OSRM) et, si `--osrm` répond, sur la matrice OSRM. Meilleure connue = meilleur
objectif OR-Tools de l'instance et de la matrice. Écrit docs/BENCHMARK_TOURNEES.md.
"""

import argparse
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
from salubri_api.services.planning.distance import approx_matrix, build_matrix
from salubri_api.services.planning.vrp import (
    STRATEGIES,
    VehicleSpec,
    effective_time_limit,
    lower_bound_km,
    solve_vrp,
)
from salubri_api.services.planning.vrp_fallback import solve_fallback

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
    return f"{name} (plan v{pv.version})", nodes, params, np.concatenate([[0.0], per_pickup]), specs, tws


def _run(lim, strat, sol, dem, dur):  # type: ignore[no-untyped-def]
    km = sum(r.distance_km for r in sol.routes)
    served = sorted({x for r in sol.routes for x in r.stops})
    left_t = float(sum(dem[i] for i in sol.unserved))
    return (lim, strat, sol.objective, km, len(sol.unserved), dur, served, sol.solver, left_t)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--osrm", default="", help="URL OSRM (graphe saison sèche) ; vide = matrice approchée seule")
    a = ap.parse_args()
    rows = []
    osrm_note = "pas d'OSRM demandé (`--osrm`)"
    with get_sessionmaker()() as s:
        insts = [instance(s, n) for n in INSTANCES]
    for label0, nodes, params, dem, specs, tws in insts:
        mats = [("approchée", approx_matrix(nodes, params.season, params.flood_speed_factor))]
        if a.osrm:
            mo = build_matrix(nodes, params.season, a.osrm, 30, params.flood_speed_factor)
            if mo.mode == "osrm":
                mats.append(("OSRM", mo))
                osrm_note = f"OSRM {a.osrm}"
            else:
                osrm_note = f"OSRM {a.osrm} injoignable : matrice approchée seule"
        for mname, m in mats:
            label = f"{label0}, matrice {mname}"
            runs = []
            for lim in LIMITS:
                for strat in STRATEGIES:
                    t0 = time.perf_counter()
                    sol = solve_vrp(
                        m.distance_km, m.duration_min, dem, specs, tws, 10, time_limit_s=lim, first_solution=strat
                    )
                    runs.append(_run(lim, strat, sol, dem, time.perf_counter() - t0))
                    print(label, lim, strat, round(sol.objective), flush=True)
            t0 = time.perf_counter()
            fb = solve_fallback(m.distance_km, m.duration_min, dem, specs, tws, 10)
            runs.append(_run(0, "heuristique de repli (sans OR-Tools)", fb, dem, time.perf_counter() - t0))
            valid = [r for r in runs if r[7] == "ortools"]
            best = min(r[2] for r in valid) if valid else min(r[2] for r in runs)
            cap = max(v.capacity_t for v in specs)
            rows.append((label, len(dem) - 1, len(specs), runs, best, cap, m, dem))
    out = [
        "<!-- SPDX-License-Identifier: CC-BY-4.0 -->",
        "# Banc d'essai des tournées",
        "",
        f"Généré par `scripts/benchmark_tournees.py` le {date.today().isoformat()} (2 cœurs ; {osrm_note}). "
        "Matrice approchée = vol d'oiseau × détour (repli sans OSRM). Objectif OR-Tools = coût (carburant au km + coût fixe des camions sortis + "
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
            "| Solveur, limite (effective) | Départ | Objectif | Écart à la meilleure connue | km | Borne inf. km "
            "| Desservis | Tonnes non desservies | Durée |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for lim, strat, obj, km, unserved, dur, served, solver, left_t in runs:
            lb = lower_bound_km(m.distance_km, dem, served, cap)
            eff = effective_time_limit(lim, len(dem))
            if solver == "ortools":
                gap, sv = f"{100 * (obj - best) / best:.1f} %", f"OR-Tools {lim} s ({eff:g} s)"
            elif lim == 0:  # heuristique seule : objectif sans pénalités, comparer km et tonnes non desservies
                gap, sv = "— (objectif sans pénalité)", "repli"
            else:
                gap, sv, strat = "— (repli)", f"OR-Tools {lim} s ({eff:g} s)", f"{strat} → heuristique de repli"
            out.append(
                f"| {sv} | {strat} | {obj:,.0f} | {gap} | {km:.1f} | {lb:.1f} "
                f"| {npts - unserved} / {npts} | {left_t:.1f} | {dur:.1f} s |".replace(",", " ")
            )
        out.append("")
    pilot = rows[0]
    gap1 = min(100 * (r[2] - pilot[4]) / pilot[4] for r in pilot[3] if r[0] == 1 and r[7] == "ortools")
    fbp = next(r for r in pilot[3] if r[0] == 0)
    bestp = min((r for r in pilot[3] if r[7] == "ortools"), key=lambda r: r[2])
    city = next(r for r in rows if r[0].startswith("Ville"))
    served_best = max(city[1] - r[4] for r in city[3])
    out += [
        "## Lecture",
        "",
        f"- **Zone pilote** : à 1 s, la meilleure stratégie est à {gap1:.1f} % de la meilleure solution connue.",
        f"- **Ville entière (démo)** : la flotte de démonstration ({city[2]} camions) ne dessert que "
        f"{served_best} points sur {city[1]} par jour d'enlèvement ; l'objectif est dominé par la pénalité des points "
        "non desservis. Ce n'est pas un défaut du solveur : il manque des camions (ou des rotations) pour la ville. "
        "À reprendre avec la vraie flotte de la mairie.",
        f"- **Heuristique de repli** (zone pilote) : {fbp[3]:.1f} km et {fbp[8]:.1f} t non desservies, contre "
        f"{bestp[3]:.1f} km et {bestp[8]:.1f} t pour la meilleure exécution OR-Tools : c'est le prix d'une panne "
        "d'OR-Tools, pas le fonctionnement normal.",
        "- **Avec / sans OSRM** : "
        + (
            "voir les sections « matrice OSRM »."
            if any("OSRM" in r[0] for r in rows)
            else "OSRM n'était pas joignable là où ce banc a tourné ; relancer avec `--osrm` sur la machine de "
            "démonstration (à faire par l'équipe). Le facteur de détour du repli est calé par "
            "`scripts/calibrer_detour.py` (`docs/DETOUR_CALIBRATION.md`)."
        ),
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
