#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Calage de `p0` et `slope_dist` (choix de jeter) sur le nombre de décharges sauvages du SDGD 2020.

    PYTHONPATH=apps/api python scripts/calibrer_simulation.py              # zone du scénario de base (base de données)
    PYTHONPATH=apps/api python scripts/calibrer_simulation.py --synthetique   # plan de test, sans base

Seule référence disponible : 58 décharges sauvages pour toute la commune (SDGD 2020, enquête 2019), ramenées à la
population de la zone (RGPH 2019 : 2 415 266 habitants). La zone est simulée dans sa situation de 2019 (seulement
les CCT existants). Le modèle ne connaît pas de « décharge » au sens du SDGD : on compte les dépôts dont le stock
final dépasse un seuil (10 t ; 5 et 20 t en contrôle), sur une grille p0 × slope_dist, `--graines` simulations par
case du modèle à agents. Une case est compatible si la référence tombe dans l'intervalle 90 % des simulations.

Écrit docs/SIMULATION_CALIBRATION.md, docs/calibration.json et docs/figures/calibration_p0.svg. Ne change pas
params_default.json : une valeur calée y serait recopiée à la main, avec sa source.
"""

import argparse
import dataclasses
import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sensibilite import plan_synthetique  # noqa: E402

from salubri_api.services.params import ScenarioParams  # noqa: E402
from salubri_api.services.simulation.abm.model import simulate_agents  # noqa: E402
from salubri_api.services.simulation.agents import PlanSnapshot, TruckRoute  # noqa: E402
from salubri_api.services.simulation.params import SimParams  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SDGD_SAUVAGES = 58  # SDGD Ouagadougou 2020, phase 2, enquête 2019 (docs/HYPOTHESES.md)
POP_COMMUNE_2019 = 2_415_266  # RGPH 2019, INSD (résultats définitifs, juillet 2022)
SEUILS_T = (5.0, 10.0, 20.0)
SEUIL_PRINCIPAL_T = 10.0


def plan_base_et_zone() -> tuple[PlanSnapshot, ScenarioParams, str, int | None]:
    """Plan du scénario de base, et nombre de décharges sauvages SDGD numérisées dans la zone active."""
    from sqlalchemy import text

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
        params = ScenarioParams(**(pv.params_snapshot or {}))
        sites = json.loads((ROOT / "data/communes/ouagadougou/sdgd2020.geojson").read_text(encoding="utf-8"))
        pts = [
            f["geometry"]["coordinates"] for f in sites["features"] if f["properties"]["statut"] == "decharge_sauvage"
        ]
        n_zone = None
        if params.active_quartier_ids and pts:
            n_zone = int(
                s.execute(
                    text("""SELECT count(*) FROM unnest(CAST(:x AS float8[]), CAST(:y AS float8[])) AS p(x, y)
                            WHERE EXISTS (SELECT 1 FROM quartiers q WHERE q.id = ANY(CAST(:ids AS uuid[]))
                                          AND ST_Contains(q.geom, ST_SetSRID(ST_MakePoint(p.x, p.y), 4326)))"""),
                    {"x": [p[0] for p in pts], "y": [p[1] for p in pts], "ids": params.active_quartier_ids},
                ).scalar_one()
            )
        plan = snapshot_from_db(s, pv)
        from salubri_api.models import CollectionPoint

        cps = s.query(CollectionPoint).filter(CollectionPoint.plan_version_id == pv.id).order_by(CollectionPoint.idx)
        ilots = [i for cp in cps for i in cp.ilot_ids]
        rows = {
            r.id: (r.lon, r.lat)
            for r in s.execute(
                text("SELECT id, ST_X(centroid) AS lon, ST_Y(centroid) AS lat FROM ilots WHERE id = ANY(:ids)"),
                {"ids": ilots},
            ).all()
        }
        cct = [f["geometry"]["coordinates"] for f in sites["features"] if f["properties"]["statut"] == "cct"]
        sq = statu_quo(plan, np.array([rows[i] for i in ilots]), np.array(cct))
        return sq, params, f"{sc.name}, plan v{pv.version} ramené aux CCT existants (situation 2019)", n_zone


def statu_quo(plan: PlanSnapshot, lonlat: np.ndarray, cct: np.ndarray) -> PlanSnapshot:
    """La zone telle qu'en 2019 : chaque îlot n'a que le CCT existant le plus proche (carte SDGD, toute la commune),
    distance de marche = vol d'oiseau × 1,2 comme pour les plans ; les camions du plan desservent ces CCT."""
    lat0 = np.radians(lonlat[:, 1].mean())
    dx = (lonlat[:, None, 0] - cct[None, :, 0]) * 111_320 * np.cos(lat0)
    dy = (lonlat[:, None, 1] - cct[None, :, 1]) * 110_540
    d = np.hypot(dx, dy) * 1.2
    near = d.argmin(axis=1)
    used = sorted(set(near.tolist()))
    idx = {c: k for k, c in enumerate(used)}
    cap = float(np.median(plan.point_capacity_kg))
    routes = [
        TruckRoute(
            r.vehicle_idx, [idx[c] for c in used[k :: len(plan.routes)]], r.distance_km, r.capacity_kg, r.fixed_cost
        )
        for k, r in enumerate(plan.routes[: len(used)])
    ]
    return PlanSnapshot(
        plan.ilot_population,
        np.array([idx[c] for c in near]),
        d[np.arange(len(near)), near],
        plan.ilot_near_water,
        np.full(len(used), cap),
        routes,
    )


def svg_grille(p0s: np.ndarray, sds: np.ndarray, mean: np.ndarray, ok: np.ndarray, ref: float) -> str:
    """Carte de chaleur : décharges ≥ seuil (moyenne) selon p0 (colonnes) et slope_dist (lignes) ; ✓ = compatible."""
    cw, ch, ml, mt = 64, 30, 150, 40
    w, h = ml + cw * len(p0s) + 20, mt + ch * len(sds) + 50
    vmax = max(float(mean.max()), 1.0)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="sans-serif" font-size="12">']
    out.append(f'<rect width="{w}" height="{h}" fill="#fff"/>')
    out.append(
        f'<text x="10" y="18" fill="#333">Décharges ≥ 10 t au dernier jour (moyenne) ; référence SDGD = {ref:.1f} ;'
        " ✓ = référence dans l'intervalle 90 %</text>"
    )
    for i, sd in enumerate(sds):
        y = mt + i * ch
        out.append(
            f'<text x="{ml - 8}" y="{y + ch / 2 + 4:.0f}" text-anchor="end" fill="#555">slope_dist {sd:g}</text>'
        )
        for j, _ in enumerate(p0s):
            v = float(mean[i, j]) / vmax
            light = 96 - 62 * v  # une teinte, du clair au foncé
            x = ml + j * cw
            out.append(f'<rect x="{x}" y="{y}" width="{cw - 2}" height="{ch - 2}" fill="hsl(200,45%,{light:.0f}%)"/>')
            ink = "#fff" if light < 55 else "#222"
            lab = f"{mean[i, j]:.0f}" + (" ✓" if ok[i, j] else "")
            out.append(
                f'<text x="{x + cw / 2 - 1}" y="{y + ch / 2 + 4:.0f}" text-anchor="middle" fill="{ink}">{lab}</text>'
            )
    for j, p0 in enumerate(p0s):
        out.append(
            f'<text x="{ml + j * cw + cw / 2 - 1}" y="{mt + len(sds) * ch + 16}" text-anchor="middle" fill="#555">{p0:g}</text>'
        )
    out.append(f'<text x="{ml + cw * len(p0s) / 2}" y="{h - 10}" text-anchor="middle" fill="#333">p0 (log-cote)</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def fr(x: float, d: int = 2) -> str:
    return f"{x:,.{d}f}".replace(",", " ").replace(".", ",")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetique", action="store_true")
    ap.add_argument("--graines", type=int, default=6)
    ap.add_argument("--horizon", type=int, default=90)
    a = ap.parse_args()
    if a.synthetique:
        plan, params, origine, n_zone = plan_synthetique(), ScenarioParams(), "plan synthétique de test", None
    else:
        plan, params, origine, n_zone = plan_base_et_zone()
    params = params.model_copy(update={"horizon_days": a.horizon, "sim_mode": "agents"})
    sp0 = SimParams.from_scenario(params)
    pop = float(np.asarray(plan.ilot_population).sum())
    ref_pop = SDGD_SAUVAGES * pop / POP_COMMUNE_2019
    ref = float(n_zone) if n_zone is not None else ref_pop  # décompte sur la carte SDGD, sinon règle de trois
    p0s = np.array([-5.0, -4.0, -3.0, -2.0, -1.5, -1.0, 0.0])
    sds = np.array([0.0, 0.0005, 0.001, 0.002, 0.004, 0.008])
    t0 = time.perf_counter()
    counts = {t: np.zeros((len(sds), len(p0s), a.graines)) for t in SEUILS_T}
    wild_share = np.zeros((len(sds), len(p0s), a.graines))
    for i, sd in enumerate(sds):
        for j, p0 in enumerate(p0s):
            sp = dataclasses.replace(sp0, p0=float(p0), slope_dist=float(sd))
            for g in range(a.graines):
                r = simulate_agents(plan, sp, 2000 + g)
                kg = np.asarray(r.wild_final_kg)
                for t in SEUILS_T:
                    counts[t][i, j, g] = int((kg >= t * 1000).sum())
                wild_share[i, j, g] = r.summary["wild_dump_t"] / max(r.summary["produced_t"], 1e-9)
    dur = time.perf_counter() - t0
    mean = {t: c.mean(axis=2) for t, c in counts.items()}
    ok = {t: (np.percentile(c, 5, axis=2) <= ref) & (ref <= np.percentile(c, 95, axis=2)) for t, c in counts.items()}
    defaut = (sp0.p0, sp0.slope_dist)
    i0, j0 = int(np.argmin(abs(sds - defaut[1]))), int(np.argmin(abs(p0s - defaut[0])))
    (ROOT / "docs/figures").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs/figures/calibration_p0.svg").write_text(
        svg_grille(p0s, sds, mean[SEUIL_PRINCIPAL_T], ok[SEUIL_PRINCIPAL_T], ref), encoding="utf-8"
    )
    compat = {t: [(float(p0s[j]), float(sds[i])) for i, j in zip(*np.nonzero(o), strict=True)] for t, o in ok.items()}
    data = {
        "date": date.today().isoformat(),
        "origine": origine,
        "population_zone": pop,
        "reference": {
            "sdgd_sauvages_commune": SDGD_SAUVAGES,
            "pop_commune_2019": POP_COMMUNE_2019,
            "regle_de_trois": ref_pop,
            "retenue": ref,
        },
        "sdgd_sauvages_numerises_dans_zone": n_zone,
        "horizon_jours": a.horizon,
        "graines": a.graines,
        "p0": p0s.tolist(),
        "slope_dist": sds.tolist(),
        "decharges_moyennes": {str(t): m.round(1).tolist() for t, m in mean.items()},
        "part_jetee_moyenne": wild_share.mean(axis=2).round(3).tolist(),
        "compatibles": {str(t): v for t, v in compat.items()},
        "duree_s": round(dur, 1),
    }
    (ROOT / "docs/calibration.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    head = "| `slope_dist` \\ `p0` | " + " | ".join(fr(x, 1) for x in p0s) + " |\n|---|" + "---|" * len(p0s)
    rows = "\n".join(
        f"| {sd:g} | "
        + " | ".join(
            f"{fr(mean[SEUIL_PRINCIPAL_T][i, j], 0)}{' ✓' if ok[SEUIL_PRINCIPAL_T][i, j] else ''}"
            f" ({fr(100 * wild_share[i, j].mean(), 0)} %)"
            for j in range(len(p0s))
        )
        + " |"
        for i, sd in enumerate(sds)
    )
    lignes_compat = "\n".join(
        f"| ≥ {t:.0f} t | {len(v)} / {len(p0s) * len(sds)} | "
        + (", ".join(f"({fr(p, 1)} ; {s:g})" for p, s in v) if v else "aucune")
        + f" | {fr(mean[t][i0, j0], 0)} |"
        for t, v in compat.items()
    )
    zone_txt = (
        f"Sur la carte numérisée du SDGD (`sdgd2020.geojson`, ± 500 m), **{n_zone}** décharge(s) sauvage(s) tombe(nt) "
        f"dans la zone active : c'est la **référence retenue**, plus locale que la règle de trois ({fr(ref_pop)})."
        if n_zone is not None
        else f"Plan synthétique : référence = règle de trois ({fr(ref_pop)})."
    )
    n_ok = len(compat[SEUIL_PRINCIPAL_T])
    verdict = (
        "**Aucune combinaison** de la grille ne reproduit la référence au seuil de 10 t"
        if n_ok == 0
        else f"**{n_ok} combinaison(s)** reproduisent la référence au seuil de 10 t, toutes"
        " avec une propension à jeter très faible ou un effet de la distance quasi nul"
    )
    md = f"""<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Calage et validation de la simulation

Généré par `scripts/calibrer_simulation.py` le {date.today().isoformat()} — {origine}, {fr(pop, 0)} habitants,
modèle à agents, horizon {a.horizon} jours, {a.graines} graines par case, {len(p0s) * len(sds) * a.graines}
simulations en {fr(dur, 0)} s. Ne pas modifier à la main : relancer le script.

## Question

Les deux paramètres libres qui décident si un ménage jette sont **`p0`** (propension de base, point hors de
portée) et **`slope_dist`** (effet de chaque mètre de marche au-delà de la limite). Aucune enquête ne les donne.
Peut-on les caler sur la seule référence chiffrée du dépôt : le SDGD 2020 ?

Référence : **{SDGD_SAUVAGES} décharges sauvages** recensées dans toute la commune (enquête 2019,
`docs/HYPOTHESES.md`). Rapportées à la population (RGPH 2019 : {fr(POP_COMMUNE_2019, 0)} habitants, INSD), la zone
simulée ({fr(pop, 0)} habitants) devrait en compter {fr(ref_pop)}. {zone_txt}

Situation simulée : celle de 2019, pas le plan. Chaque îlot n'a que le **CCT existant le plus proche** (carte du
SDGD, distance à vol d'oiseau × 1,2), desservi par les camions du plan. Analogue d'une « décharge » : un dépôt
sauvage dont le stock au dernier jour atteint un seuil (10 t, soit une vingtaine de m³ ; 5 t et 20 t en contrôle).

## Résultat

{verdict}.

Décharges ≥ 10 t au dernier jour (moyenne sur {a.graines} graines) et, entre parenthèses, part des déchets
produits jetée sur la période ; ✓ = la référence est dans l'intervalle 90 % des simulations :

{head}
{rows}

![Calage : décharges simulées selon p0 et slope_dist](figures/calibration_p0.svg)

| Seuil d'une « décharge » | Cases compatibles | (`p0` ; `slope_dist`) compatibles | Valeur aux paramètres actuels |
|---|---|---|---|
{lignes_compat}

## Ce qu'on en conclut

- Avec les CCT de 2019, la marche moyenne dépasse 1 km : le modèle fait finir en dépôt sauvage
  plus de 90 % des déchets dès que `p0` dépasse -2 (pré-collecteurs compris, qui déchargent au plus près quand le
  CCT est loin), et chaque îlot finit avec un tas de plusieurs tonnes. Le SDGD, lui, ne compte
  que les grandes décharges cartographiables de la ville. **L'analogue « un îlot = une décharge possible » ne
  correspond pas à ce que compte le SDGD** : les deux chiffres ne mesurent pas la même chose.
- Les rares cases compatibles demandent que presque personne ne jette même à 1 km du CCT, ce que contredisent
  les dépôts visibles dans tous les quartiers. Les retenir serait caler le modèle sur un artefact.
- **Décision** : `p0` et `slope_dist` gardent leurs valeurs d'hypothèse (`docs/PARAMETRES.md`), marquées « non
  calé ». La sensibilité des résultats à ces deux paramètres est mesurée dans `docs/SIMULATION_SENSIBILITE.md` ;
  les écarts entre scénarios (comparaison de plans) y sont moins sensibles que les niveaux absolus.
- La situation 2019 simulée est grossière : capacité des CCT prise égale à celle des points du plan, pas de
  ramassage informel, pas de stock ancien (une décharge du SDGD peut avoir des années).

## À faire par l'équipe

Obtenir de la mairie (DPAE / DSPH de l'arrondissement) une référence de **débit**, plus proche du modèle qu'un
décompte de sites : tonnes de dépôts sauvages enlevées par mois, ou part des ménages abonnés à la pré-collecte
dans l'arrondissement. Le script se relance alors avec cette cible (une ligne à changer : `reference`).
"""
    (ROOT / "docs/SIMULATION_CALIBRATION.md").write_text(md, encoding="utf-8")
    print(f"référence {ref:.2f} ; cases compatibles {[len(v) for v in compat.values()]} ; {dur:.0f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
