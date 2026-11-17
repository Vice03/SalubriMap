# SPDX-License-Identifier: AGPL-3.0-or-later
"""Placement CP-SAT sur de petites instances dont on connaît l'optimum (énumération)."""

import itertools

import numpy as np

from salubri_api.services.params import ScenarioParams
from salubri_api.services.planning.collection_points import M_PER_DEG, PlacedPoint, place_points
from salubri_api.services.planning.placement_opt import cost_matrix, optimise

RNG = np.random.default_rng(3)
XY = RNG.uniform(0, 1000, (12, 2))
W = RNG.uniform(0.5, 2.0, 12)
CAND = RNG.uniform(0, 1000, (8, 2))


def brute(xy, w, cand, walk, max_pts, open_cost, penalty=10.0):  # type: ignore[no-untyped-def]
    d = cost_matrix(xy, cand)
    best = np.inf
    for k in range(1, max_pts + 1):
        for s in itertools.combinations(range(len(cand)), k):
            di = d[:, list(s)].min(1)  # capacité non contraignante : le plus proche
            best = min(best, (w * di * (1 + penalty * (di > walk))).sum() + open_cost * k)
    return best


def test_optimum_egal_a_l_enumeration() -> None:
    r = optimise(XY, W, CAND, cap_week=1e6, walk_max=300, max_points=3, open_cost=500, k_nearest=8)
    assert r.status == "optimal" and r.gap < 1e-6
    assert abs(r.objective - brute(XY, W, CAND, 300, 3, 500)) < 1  # entiers : 0,1 t·m près par paire


def test_capacite_oblige_a_ouvrir_plus() -> None:
    xy = np.array([[0.0, 0], [10, 0], [20, 0], [30, 0]])
    cand = np.array([[15.0, 0], [0, 0], [30, 0]])
    w = np.ones(4)
    one = optimise(xy, w, cand, cap_week=10, walk_max=300, max_points=3, open_cost=1000, k_nearest=3)
    two = optimise(xy, w, cand, cap_week=2, walk_max=300, max_points=3, open_cost=1000, k_nearest=3)
    assert one.open == [0] and len(two.open) == 2
    assert np.bincount(two.assignment).max() <= 2


def test_couverture_penalisee_ouvre_un_point_isole() -> None:
    xy = np.array([[0.0, 0], [5, 0], [2000, 0]])
    cand = np.array([[2.0, 0], [1990, 0]])
    r = optimise(xy, np.ones(3), cand, cap_week=100, walk_max=300, max_points=2, open_cost=200, k_nearest=2)
    assert sorted(r.open) == [0, 1] and r.uncovered_t == 0


def test_maximum_et_points_figes() -> None:
    r = optimise(XY, W, CAND, cap_week=1e6, walk_max=300, max_points=2, fixed=[5], open_cost=0, k_nearest=8)
    assert 5 in r.open and len(r.open) <= 2


def test_stabilite_garde_le_point_existant() -> None:
    xy = np.array([[0.0, 0], [100, 0]])
    cand = np.array([[60.0, 0], [50, 0]])  # 0 = point existant, 1 = un peu mieux placé
    kw = dict(cap_week=10, walk_max=300, max_points=1, open_cost=0, k_nearest=2)
    assert optimise(xy, np.ones(2), cand, stability={0: 0.0}, **kw).open == [1]
    assert optimise(xy, np.ones(2), cand, stability={0: 100.0}, **kw).open == [0]


def test_place_points_avec_candidats_ne_fait_pas_pire_que_le_kmeans() -> None:
    lon0, lat0 = -1.52, 12.37
    ll = np.column_stack([lon0 + XY[:, 0] / M_PER_DEG, lat0 + XY[:, 1] / M_PER_DEG])
    demand = W * 1000 / 7  # kg/j
    p = ScenarioParams(collection_point_capacity_t=2.5, pickup_frequency_per_week=2, walk_distance_max_m=300)
    grid = [(lon0 + x / M_PER_DEG, lat0 + y / M_PER_DEG) for x in range(0, 1001, 50) for y in range(0, 1001, 50)]
    km = place_points(ll, demand, p)
    opt = place_points(ll, demand, p, candidates=lambda _bbox: grid)
    info = opt.optimisation
    assert info is not None and info["statut"] in ("optimal", "faisable") and info["depart"] == "k-means"
    assert info["objectif"] <= info["objectif_depart"] * 1.001  # coûts arrondis à 0,1 t·m par paire
    assert info["borne"] <= info["objectif"] + 1e-6
    assert len(opt.assignment) == 12 and all(q.key.startswith("P") for q in opt.points)
    # les points précédents restent en place quand la stabilité est forte
    prev = [PlacedPoint(q.key, q.lon, q.lat, 2.5) for q in opt.points]
    again = place_points(
        ll, demand, p.model_copy(update={"placement_stability_m": 2000}), candidates=lambda _b: grid, previous=prev
    )
    assert {q.key for q in again.points} == {q.key for q in prev}
    assert len(km.points) >= 1


def test_capacite_dure_jamais_depassee_ou_infaisabilite_dite() -> None:
    """Étape 0.2 : avec `hard_capacity`, aucun point ne dépasse sa capacité ; sinon le statut dit « infaisable »."""
    xy = np.array([[0.0, 0], [10, 0], [20, 0], [30, 0]])
    cand = np.array([[15.0, 0], [0, 0], [30, 0]])
    w = np.ones(4)
    r = optimise(xy, w, cand, cap_week=2, walk_max=300, max_points=2, open_cost=1, k_nearest=3, hard_capacity=True)
    load = np.bincount(r.assignment, weights=w)
    assert r.status in ("optimal", "faisable") and (load <= 2 + 1e-9).all() and r.overload_t == 0
    soft = optimise(xy, w, cand, cap_week=1.5, walk_max=300, max_points=2, open_cost=1, k_nearest=3)
    hard = optimise(xy, w, cand, cap_week=1.5, walk_max=300, max_points=2, open_cost=1, k_nearest=3,
                    hard_capacity=True)  # fmt: skip
    assert soft.overload_t > 0  # l'ancien comportement débordait
    assert hard.status == "infaisable" and hard.open == []


def test_frequence_effective() -> None:
    from salubri_api.services.planning.collection_points import effective_frequency, frequencies

    assert frequencies(2, 3) == [2.0, 3.0] and frequencies(2.5, 4) == [2.5, 3.0, 4.0] and frequencies(3, 3) == [3.0]
    cap = np.array([2.5, 2.5])
    assert effective_frequency(np.array([4.0, 5.0]), cap, 2, 3) == (2.0, [])
    assert effective_frequency(np.array([4.0, 6.0]), cap, 2, 3) == (3.0, [])  # 6 t ÷ 2 > 2,5 t ; ÷ 3 tient
    assert effective_frequency(np.array([4.0, 9.0]), cap, 2, 3) == (3.0, [1])  # 9 ÷ 3 = 3 t : déborde encore


def test_placement_monte_a_trois_enlevements_plutot_que_deborder() -> None:
    """Demande trop forte pour 2 enlèvements avec le nombre maximal de points : le placement passe à 3."""
    rng = np.random.default_rng(1)
    lonlat = np.column_stack([-1.52 + rng.uniform(0, 0.01, 40), 12.37 + rng.uniform(0, 0.01, 40)])
    kg_day = np.full(40, 600 / 7)  # 0,6 t/semaine par îlot, 24 t au total
    road = [(-1.52 + i * 0.001, 12.37 + j * 0.001) for i in range(11) for j in range(11)]
    p = ScenarioParams(collection_point_capacity_t=2.5, collection_point_max=4, pickup_frequency_per_week=2,
                       pickup_frequency_max_per_week=3, walk_distance_max_m=600, placement_time_limit_s=2)  # fmt: skip
    res = place_points(lonlat, kg_day, p, candidates=lambda bbox: road)
    cap = res.optimisation["capacite"]  # type: ignore[index]
    assert cap["contrainte"] == "dure" and cap["enlevements_semaine"] == 3.0  # 4 points × 2,5 t × 2 = 20 t < 24 t
    assert all(q.demand_t_week / 3 <= 2.5 + 1e-6 for q in res.points)
