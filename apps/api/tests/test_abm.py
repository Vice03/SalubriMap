# SPDX-License-Identifier: AGPL-3.0-or-later
"""Modèle à agents (docs/SIMULATION_ODD.md) : bilan de masse, reproductibilité, règles, cohérence, vitesse."""

import dataclasses
import time

import numpy as np
import pytest
from tests.test_simulation import PLAN, plan, sp

from salubri_api.services.params import ScenarioParams
from salubri_api.services.simulation.abm.model import _fill, simulate_agents
from salubri_api.services.simulation.abm.params import AbmParams
from salubri_api.services.simulation.agents import PlanSnapshot, TruckRoute
from salubri_api.services.simulation.engine import replicate, simulate
from salubri_api.services.simulation.params import SimParams

HOM = AbmParams(heterogeneite=False)


def mean(key: str, p: SimParams, ap: AbmParams | None = None, n: int = 10, pl: PlanSnapshot = PLAN) -> float:
    return float(np.mean([simulate_agents(pl, p, s, ap).summary[key] for s in range(n)]))


@pytest.mark.parametrize("ap", [AbmParams(), HOM], ids=["hétérogène", "homogène"])
def test_bilan_de_masse_exact(ap: AbmParams) -> None:
    for kw in ({}, {"season": "rain", "truck_breakdown_rate_per_day": 0.5}, {"subscription_fee_fcfa_month": 0}):
        assert simulate_agents(PLAN, sp(**kw), 3, ap).summary["mass_balance_error"] < 1e-9


def test_meme_graine_meme_resultat() -> None:
    a, b = simulate_agents(PLAN, sp(), 7), simulate_agents(PLAN, sp(), 7)
    assert a.summary == b.summary and a.daily == b.daily
    assert simulate_agents(PLAN, sp(), 8).summary != a.summary


def test_remplissage_dans_l_ordre_par_groupe() -> None:
    acc = _fill(np.array([1, 0, 1, 0]), np.array([5.0, 4.0, 5.0, 4.0]), np.array([6.0, 7.0]))
    assert acc.tolist() == [5.0, 4.0, 2.0, 2.0]


def test_coherence_avec_le_modele_agrege() -> None:
    """ODD § 8 : hétérogénéité coupée, moyenne de 30 réplications à ±10 % du modèle agrégé."""
    p = sp()
    agr = simulate(PLAN, p, 42).summary
    runs = [simulate_agents(PLAN, p, s, HOM).summary for s in range(30)]
    for k in ("produced_t", "collected_t", "precollected_t", "wild_dump_t", "cleanup_t"):
        m = np.mean([r[k] for r in runs])
        assert abs(m - agr[k]) <= 0.10 * agr[k], (k, m, agr[k])
    sub = np.mean([r["subscription_rate_final"] for r in runs])
    assert abs(sub - agr["subscription_rate_final"]) <= 0.05


def test_menages_loin_du_point_jettent_plus() -> None:
    near = mean("wild_dump_t", sp(walk_distance_max_m=1000))
    far = mean("wild_dump_t", sp(walk_distance_max_m=100))
    assert far > 1.3 * near


def test_norme_sociale_et_habitude_entretiennent_les_depots() -> None:
    sans = mean("wild_dump_t", sp(), AbmParams(beta_norme=0, beta_habitude=0))
    avec = mean("wild_dump_t", sp(), AbmParams(beta_norme=4, beta_habitude=1))
    assert avec > sans


def test_saison_des_pluies_plus_de_dechets_et_de_depots() -> None:
    sec, pluie = simulate_agents(PLAN, sp(), 1).summary, simulate_agents(PLAN, sp(season="rain"), 1).summary
    assert pluie["produced_t"] == pytest.approx(1.15 * sec["produced_t"], abs=0.02)  # résumé arrondi à 10 kg
    assert mean("wild_dump_t", sp(season="rain")) > mean("wild_dump_t", sp())


def test_laabal_dissuade_et_met_a_l_amende() -> None:
    """La crainte de l'amende entre dans le choix : à descentes égales, plus de dissuasion → moins de dépôts.

    (Effet net des descentes : voir docs/SIMULATION_ODD.md § 11 — le dépotoir rapporté au point peut le faire
    déborder, ce qui compense une dissuasion faible.)"""
    off = sp(laabal_operations_per_week=0)
    on = sp(laabal_operations_per_week=7, laabal_deterrence=0.8)
    r = simulate_agents(PLAN, on, 1).summary
    assert r["laabal_controls"] > 0 and r["laabal_fines"] > 0
    assert simulate_agents(PLAN, off, 1).summary["laabal_fines"] == 0
    assert mean("wild_dump_t", on) < mean("wild_dump_t", sp(laabal_operations_per_week=7, laabal_deterrence=0))


def test_prix_eleve_moins_d_abonnes() -> None:
    assert mean("subscription_rate_final", sp(subscription_fee_fcfa_month=6000)) < mean(
        "subscription_rate_final", sp(subscription_fee_fcfa_month=500)
    )


def test_pre_collecteurs_non_rentables_abandonnent() -> None:
    r = simulate_agents(PLAN, sp(subscription_fee_fcfa_month=100), 1)
    assert r.summary["precollectors_dropped"] > 0
    assert r.daily["precollectors_active"][-1] < r.daily["precollectors_active"][0]


def test_pre_collecteur_rentable_reprend_les_ilots_d_un_voisin_parti() -> None:
    """Îlots 0–14 peu peuplés (leur collecteur fait faillite), îlots 15–29 très peuplés (rentable, charrette vide)."""
    n = 30
    pop = np.r_[np.full(15, 20.0), np.full(15, 400.0)]
    pl = PlanSnapshot(pop, np.arange(n) // 2, np.full(n, 100.0), np.zeros(n, bool), np.full(15, 1e6), [])
    p = sp(precollector_capacity_t=50, precollector_cost_fcfa_month=30000, horizon_days=150)
    sans = AbmParams(extension_marge=1e9)
    on = [simulate_agents(pl, p, s).daily["precollected_t"] for s in range(5)]
    off = [simulate_agents(pl, p, s, sans).daily["precollected_t"] for s in range(5)]
    assert np.mean([sum(x[90:]) for x in on]) > np.mean([sum(x[90:]) for x in off])


def test_camions_en_panne_rien_ne_part_en_decharge() -> None:
    r = simulate_agents(PLAN, sp(truck_breakdown_rate_per_day=1.0), 1).summary
    assert r["collected_t"] == 0 and r["overflow_point_days"] > 0


def test_budget_epuise_plus_de_tournees() -> None:
    r = simulate_agents(PLAN, sp(budget_fcfa_month=0), 1).summary
    assert r["collected_t"] == 0


def test_un_arrondissement_en_moins_de_30_s() -> None:
    rng = np.random.default_rng(0)
    n, p = 650, 90  # ~130 000 habitants, ~19 000 ménages
    pl = PlanSnapshot(
        rng.uniform(150, 250, n),
        rng.integers(0, p, n),
        rng.uniform(50, 600, n),
        rng.random(n) < 0.1,
        np.full(p, 2500.0),
        [TruckRoute(i % 12, list(range(i * 4, min(p, i * 4 + 4))), 25, 8000, 20000) for i in range(23)],
    )
    t0 = time.perf_counter()
    r = simulate_agents(pl, SimParams.from_scenario(ScenarioParams(horizon_days=90)), 1)
    assert time.perf_counter() - t0 < 30
    assert r.summary["households"] > 15_000


def test_replications_intervalle_a_90_pourcent() -> None:
    res = replicate(plan(), sp(horizon_days=30), 1, 30, mode="agents")
    s = res["summary"]["wild_dump_t"]
    assert s["p5"] <= s["p10"] <= s["median"] <= s["p90"] <= s["p95"]
    assert s["p5"] < s["p95"]  # les agents donnent une vraie dispersion
    assert res["replications"] == 30 and res["mode"] == "agents"
    assert len(res["daily"]["wild_new_t"]["p95"]) == 30


def test_indicateurs_demandes() -> None:
    r = simulate_agents(PLAN, sp(), 1)
    for k in (
        "produced_t",
        "collected_t",
        "wild_dump_t",
        "cleanup_t",
        "wild_dumps_active_mean",
        "subscription_rate_final",
        "precollector_income_mean_fcfa",
        "precollectors_active_final",
        "laabal_controls",
        "cost_per_t",
        "budget_left_final_fcfa",
        "coverage_rate",
    ):
        assert k in r.summary
    for k in ("precollectors_active", "budget_left_fcfa", "laabal_fines", "coverage_rate"):
        assert len(r.daily[k]) == 90


def test_parametres_comportementaux_modifiables() -> None:
    assert dataclasses.replace(AbmParams(), beta_norme=0).beta_norme == 0
