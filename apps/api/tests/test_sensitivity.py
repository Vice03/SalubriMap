# SPDX-License-Identifier: AGPL-3.0-or-later
"""Morris et Sobol sur des fonctions dont on connaît la réponse."""

import numpy as np

from salubri_api.services.simulation.abm.sensitivity import morris, scale, sobol


def lineaire(u: np.ndarray) -> np.ndarray:  # y = 1·x1 + 3·x2 + 0·x3
    return u[:, 0] + 3 * u[:, 1]


def test_morris_retrouve_les_pentes() -> None:
    m = morris(lineaire, 3, r=8, seed=0)
    assert np.allclose(m["mu_star"], [1, 3, 0])
    assert np.allclose(m["sigma"], 0)


def test_sobol_retrouve_les_parts_de_variance() -> None:
    # Var = 1/12 + 9/12 : S1 attendus 0,1 et 0,9, rien pour x3
    s = sobol(lineaire, 3, n=4096, seed=0, boot=50)
    assert np.allclose(s["S1"], [0.1, 0.9, 0], atol=0.05)
    assert np.allclose(s["ST"], [0.1, 0.9, 0], atol=0.05)
    assert (s["ST_ic"][0] <= s["ST"] + 1e-9).all() and (s["ST"] <= s["ST_ic"][1] + 1e-9).all()


def test_interaction_vue_par_l_indice_total() -> None:
    s = sobol(lambda u: u[:, 0] * u[:, 1], 2, n=4096, seed=1, boot=10)
    assert (s["ST"] > s["S1"]).all()


def test_scale() -> None:
    assert scale(np.array([[0.0, 0.5, 1.0]]), [(0, 10), (2, 4), (-1, 1)]).tolist() == [[0, 3, 1]]
