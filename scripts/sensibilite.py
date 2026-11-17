#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sensibilité globale du modèle à agents : 30 réplications au point nominal, Morris puis Sobol sur 8 paramètres.

    PYTHONPATH=apps/api python scripts/sensibilite.py            # plan du scénario de base (base de données)
    PYTHONPATH=apps/api python scripts/sensibilite.py --synthetique   # plan de test (~19 000 ménages), sans base

Écrit docs/SIMULATION_SENSIBILITE.md, docs/sensibilite.json et docs/figures/sensibilite_sobol.svg. Le hasard propre au modèle (graines) est mesuré à part, au point
nominal : si sa variance est du même ordre que celle due aux paramètres, les indices de cette sortie sont du bruit. Chaque évaluation = moyenne de `--graines` simulations
(mêmes graines pour tous les points : nombres aléatoires communs). Durée : ~(9 × r + 10 × N) × graines + 30 simulations.
"""

import argparse
import dataclasses
import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

from salubri_api.services.params import ScenarioParams
from salubri_api.services.simulation.abm.model import simulate_agents
from salubri_api.services.simulation.abm.params import AbmParams
from salubri_api.services.simulation.abm.sensitivity import morris, scale, sobol
from salubri_api.services.simulation.agents import PlanSnapshot, TruckRoute
from salubri_api.services.simulation.params import SimParams

ROOT = Path(__file__).resolve().parents[1]
# (nom, où, bornes, libellé, pourquoi ces bornes)
FACTEURS = [
    (
        "kg_per_person_day",
        "sim",
        (0.4, 0.9),
        "Déchets par habitant (kg/j)",
        "0,6 annoncé par la mairie ; ±50 % selon quartier",
    ),
    ("subscription_rate", "sim", (0.2, 0.5), "Taux d'abonnement initial", "hypothèse 35 %, aucune enquête"),
    ("fee_fcfa_month", "sim", (500.0, 3000.0), "Prix de l'abonnement (FCFA/mois)", "tarifs observés 1 000 à 2 500"),
    ("p0", "sim", (-2.5, -0.5), "Propension de base à jeter (log-cote)", "hypothèse"),
    ("slope_dist", "sim", (0.002, 0.008), "Effet de la distance au-delà de la marche (/m)", "hypothèse"),
    ("laabal_deterrence", "sim", (0.2, 0.8), "Dissuasion d'un contrôle Laabal", "hypothèse"),
    ("beta_norme", "abm", (0.0, 4.0), "Poids de la norme sociale de l'îlot", "hypothèse"),
    ("breakdown_rate", "sim", (0.01, 0.10), "Pannes de camion (par jour)", "2 % par défaut ; parc vieillissant"),
]
SORTIES = [
    ("wild_dump_t", "Tonnes jetées en dépôt sauvage"),
    ("collected_t", "Tonnes collectées par camion"),
    ("cost_per_t", "Coût de la mairie à la tonne"),
    ("subscription_rate_final", "Taux d'abonnement final"),
]


def plan_synthetique() -> PlanSnapshot:
    rng = np.random.default_rng(0)
    n, p = 650, 90
    return PlanSnapshot(
        rng.uniform(150, 250, n),
        rng.integers(0, p, n),
        rng.uniform(50, 600, n),
        rng.random(n) < 0.1,
        np.full(p, 2500.0),
        [TruckRoute(i % 12, list(range(i * 4, min(p, i * 4 + 4))), 25, 8000, 20000) for i in range(23)],
    )


def plan_base() -> tuple[PlanSnapshot, ScenarioParams, str]:
    from salubri_api.db import get_sessionmaker
    from salubri_api.models import PlanVersion, Scenario
    from salubri_api.services.plan.pipeline import snapshot_from_db

    with get_sessionmaker()() as s:
        sc = s.query(Scenario).filter(Scenario.parent_id.is_(None)).order_by(Scenario.created_at).first()
        if sc is None:
            raise SystemExit("Aucun scénario : lancer la démo (seed) ou utiliser --synthetique")
        pv = (
            s.query(PlanVersion)
            .filter(PlanVersion.scenario_id == sc.id, PlanVersion.status == "ready")
            .order_by(PlanVersion.version.desc())
            .first()
        )
        if pv is None:
            raise SystemExit("Aucun plan prêt pour le scénario de base")
        return snapshot_from_db(s, pv), ScenarioParams(**(pv.params_snapshot or {})), f"{sc.name}, plan v{pv.version}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetique", action="store_true")
    ap.add_argument("--morris-r", type=int, default=10)
    ap.add_argument("--sobol-n", type=int, default=256)
    ap.add_argument("--graines", type=int, default=2)
    ap.add_argument("--horizon", type=int, default=90)
    ap.add_argument("--sobol-k", type=int, default=8, help="nombre de paramètres passés à Sobol (les plus influents)")
    a = ap.parse_args()
    if a.synthetique:
        plan, params, origine = plan_synthetique(), ScenarioParams(), "plan synthétique de test (650 îlots)"
    else:
        plan, params, origine = plan_base()
    params = params.model_copy(update={"horizon_days": a.horizon, "sim_mode": "agents"})
    sp0, ap0 = SimParams.from_scenario(params), AbmParams()
    names = [f[0] for f in FACTEURS]
    n_runs = 0

    def evaluate(u: np.ndarray, which: list[int]) -> np.ndarray:
        nonlocal n_runs
        out = np.zeros((len(u), len(SORTIES)))
        vals = scale(u, [FACTEURS[i][2] for i in which])
        for row, v in enumerate(vals):
            sim_kw = {FACTEURS[i][0]: float(x) for i, x in zip(which, v, strict=True) if FACTEURS[i][1] == "sim"}
            abm_kw = {FACTEURS[i][0]: float(x) for i, x in zip(which, v, strict=True) if FACTEURS[i][1] == "abm"}
            sp, abp = dataclasses.replace(sp0, **sim_kw), dataclasses.replace(ap0, **abm_kw)
            rs = [simulate_agents(plan, sp, 1000 + g, abp).summary for g in range(a.graines)]
            out[row] = [np.mean([r[k] for r in rs]) for k, _ in SORTIES]
            n_runs += a.graines
        return out

    t0 = time.perf_counter()
    cache: dict[str, np.ndarray] = {}

    def f_morris(u: np.ndarray) -> np.ndarray:
        cache["morris"] = evaluate(u, list(range(len(FACTEURS))))
        return cache["morris"][:, 0]

    mo = morris(f_morris, len(FACTEURS), r=a.morris_r, seed=1)
    # μ* pour chaque sortie (le criblage se fait sur les dépôts sauvages, sortie principale)
    mo_all = {}
    for j, (k, _) in enumerate(SORTIES):
        y = cache["morris"][:, j]
        mo_all[k] = morris(lambda _u, y=y: y, len(FACTEURS), r=a.morris_r, seed=1)["mu_star"]
    top = list(np.argsort(-mo["mu_star"])[: a.sobol_k])
    so_all = {}

    def f_sobol(u: np.ndarray) -> np.ndarray:
        cache["sobol"] = evaluate(u, top)
        return cache["sobol"][:, 0]

    so = sobol(f_sobol, len(top), n=a.sobol_n, seed=2)
    for j, (k, _) in enumerate(SORTIES):
        y = cache["sobol"][:, j]
        so_all[k] = sobol(lambda _u, y=y: y, len(top), n=a.sobol_n, seed=2)
    del so
    # hasard propre au modèle : 30 graines au point nominal ; variance de la moyenne de `graines` simulations
    nominal = [simulate_agents(plan, sp0, 5000 + g, ap0).summary for g in range(30)]
    replications = {
        k: {
            "mediane": float(np.median([r[k] for r in nominal])),
            "p5": float(np.percentile([r[k] for r in nominal], 5)),
            "p95": float(np.percentile([r[k] for r in nominal], 95)),
        }
        for k in nominal[0]
        if isinstance(nominal[0][k], int | float)
    }
    n_runs += 30
    part_hasard = {}
    for j, (k, _) in enumerate(SORTIES):
        v_tot = float(np.var(cache["sobol"][: 2 * a.sobol_n, j]))
        v_bruit = float(np.var([r[k] for r in nominal], ddof=1)) / a.graines
        part_hasard[k] = round(v_bruit / v_tot, 3) if v_tot > 0 else None
    duree = time.perf_counter() - t0

    res = {
        "date": date.today().isoformat(),
        "plan": origine,
        "horizon_jours": a.horizon,
        "graines_par_point": a.graines,
        "simulations": n_runs,
        "duree_s": round(duree, 1),
        "facteurs": [{"nom": f[0], "bornes": f[2], "libelle": f[3], "source": f[4]} for f in FACTEURS],
        "morris": {k: dict(zip(names, np.round(v, 4).tolist(), strict=True)) for k, v in mo_all.items()},
        "sobol_facteurs": [names[i] for i in top],
        "part_hasard": part_hasard,
        "replications_nominal": replications,
        "sobol": {
            k: {
                "S1": np.round(v["S1"], 3).tolist(),
                "S1_ic": np.round(v["S1_ic"], 3).tolist(),
                "ST": np.round(v["ST"], 3).tolist(),
                "ST_ic": np.round(v["ST_ic"], 3).tolist(),
            }
            for k, v in so_all.items()
        },
    }
    (ROOT / "docs/sensibilite.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (ROOT / "docs/SIMULATION_SENSIBILITE.md").write_text(rapport(res), encoding="utf-8")
    (ROOT / "docs/figures").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs/figures/sensibilite_sobol.svg").write_text(figure_sobol(res), encoding="utf-8")
    print(f"{n_runs} simulations en {duree:.0f} s ; facteurs retenus pour Sobol : {res['sobol_facteurs']}")
    return 0


def _n(x: float) -> str:
    x = 0.0 if abs(x) < 5e-4 else x
    s = f"{x:,.0f}" if abs(x) >= 100 else f"{x:.3g}"
    return s.replace(",", " ").replace(".", ",")


def figure_sobol(r: dict) -> str:
    """Barres horizontales S1 (plein) et ST (contour) pour les dépôts sauvages ; une teinte, valeurs en clair."""
    lib = {f["nom"]: f["libelle"] for f in r["facteurs"]}
    s = r["sobol"]["wild_dump_t"]
    noms = r["sobol_facteurs"]
    ml, mt, bw, bh, gap = 290, 34, 300, 16, 12
    w, h = ml + bw + 80, mt + len(noms) * (bh + gap) + 30
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="sans-serif" font-size="12">',
        f'<rect width="{w}" height="{h}" fill="#fff"/>',
        '<text x="10" y="18" fill="#333">Tonnes jetées en dépôt sauvage : S1 (plein) et ST (contour)</text>',
    ]
    for i, nom in enumerate(noms):
        y = mt + i * (bh + gap)
        s1, st = max(s["S1"][i], 0.0), max(s["ST"][i], 0.0)
        out.append(f'<text x="{ml - 8}" y="{y + bh - 3}" text-anchor="end" fill="#333">{lib[nom]}</text>')
        out.append(
            f'<rect x="{ml}" y="{y}" width="{bw * min(st, 1):.1f}" height="{bh}" fill="none" stroke="#1f6f8b" stroke-width="2" rx="2"/>'
        )
        out.append(f'<rect x="{ml}" y="{y}" width="{bw * min(s1, 1):.1f}" height="{bh}" fill="#1f6f8b" rx="2"/>')
        out.append(
            f'<text x="{ml + bw * min(max(st, s1), 1) + 6:.1f}" y="{y + bh - 3}" fill="#555">{_n(s1)} / {_n(st)}</text>'
        )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def rapport(r: dict) -> str:
    lib = {f["nom"]: f["libelle"] for f in r["facteurs"]}
    lines = [
        "<!-- SPDX-License-Identifier: CC-BY-4.0 -->",
        "# Incertitude et sensibilité du modèle à agents",
        "",
        f"Généré par `scripts/sensibilite.py` le {r['date']} — {r['plan']}, horizon {r['horizon_jours']} jours, "
        f"{r['graines_par_point']} graines par point, {r['simulations']} simulations en {_n(r['duree_s'])} s. "
        "Ne pas modifier à la main : relancer le script.",
        "",
        "## 0. Incertitude propre au modèle : 30 réplications au point nominal",
        "",
        "Mêmes paramètres, 30 graines. Médiane et intervalle à 90 % (5ᵉ – 95ᵉ centile) de chaque indicateur sur "
        "l'horizon. C'est ce que montre le tableau de bord (bandes autour des courbes).",
        "",
        "| Indicateur | Médiane | Intervalle 90 % |",
        "|---|---|---|",
        *[
            f"| `{k}` | {_n(v['mediane'])} | {_n(v['p5'])} – {_n(v['p95'])} |"
            for k, v in r["replications_nominal"].items()
        ],
        "",
        "## Paramètres étudiés",
        "",
        "| Paramètre | Bornes | Source des bornes |",
        "|---|---|---|",
        *[
            f"| {f['libelle']} (`{f['nom']}`) | {_n(f['bornes'][0])} – {_n(f['bornes'][1])} | {f['source']} |"
            for f in r["facteurs"]
        ],
        "",
        "## 1. Criblage de Morris (μ*, unités de la sortie)",
        "",
        "μ* = effet moyen absolu quand le paramètre parcourt les 2/3 de son intervalle. Plus il est grand, plus le "
        "paramètre compte.",
        "",
        "| Paramètre | " + " | ".join(lab for _, lab in SORTIES) + " |",
        "|---|" + "---|" * len(SORTIES),
    ]
    for f in r["facteurs"]:
        lines.append(f"| {f['libelle']} | " + " | ".join(_n(r["morris"][k][f["nom"]]) for k, _ in SORTIES) + " |")
    lines += [
        "",
        f"## 2. Indices de Sobol sur les {len(r['sobol_facteurs'])} paramètres, classés par Morris",
        "",
        "![Indices de Sobol, dépôts sauvages](figures/sensibilite_sobol.svg)",
        "",
        "S1 = part de la variance de la sortie due au paramètre seul ; ST = part totale, interactions comprises. "
        "Entre crochets : intervalle de confiance à 95 % (bootstrap). Avec peu d'échantillons, les intervalles "
        "sont larges : l'ordre des paramètres compte plus que les valeurs.",
        "",
    ]
    for k, lab in SORTIES:
        s = r["sobol"][k]
        ph = r["part_hasard"][k]
        note = (
            f"Hasard propre au modèle : {_n(100 * ph)} % de la variance"
            + (
                " — **indices non interprétables** (bruit du même ordre que l'effet des paramètres)."
                if ph > 0.3
                else "."
            )
            if ph is not None
            else "Sortie constante."
        )
        lines += [f"### {lab}", "", note, "", "| Paramètre | S1 | ST |", "|---|---|---|"]
        for i, nom in enumerate(r["sobol_facteurs"]):
            lines.append(
                f"| {lib[nom]} | {_n(s['S1'][i])} [{_n(s['S1_ic'][0][i])} ; {_n(s['S1_ic'][1][i])}] "
                f"| {_n(s['ST'][i])} [{_n(s['ST_ic'][0][i])} ; {_n(s['ST_ic'][1][i])}] |"
            )
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
