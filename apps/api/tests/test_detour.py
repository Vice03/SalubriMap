# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lot 5.3 : facteur de détour du repli sans OSRM, paramètre du scénario et calage sur OSRM."""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

import calibrer_detour  # noqa: E402

from salubri_api.services.params import ScenarioParams  # noqa: E402
from salubri_api.services.planning.distance import approx_matrix  # noqa: E402

NODES = [(-1.52, 12.37), (-1.50, 12.37), (-1.51, 12.39)]


def test_detour_factor_is_a_scenario_parameter() -> None:
    base = approx_matrix(NODES, "dry", detour=1.0).distance_km
    assert np.allclose(approx_matrix(NODES, "dry", detour=1.27).distance_km, base * 1.27)
    assert np.allclose(approx_matrix(NODES, "rain").distance_km, base * 1.5)  # défaut par saison
    d = ScenarioParams()
    assert (d.fallback_detour_dry, d.fallback_detour_rain) == (1.35, 1.5)


def test_calibration_takes_the_median_ratio_and_reports_the_error() -> None:
    rng = np.random.default_rng(0)
    crow = rng.uniform(0.1, 8, 500)
    road = crow * rng.normal(1.25, 0.08, 500)
    road[:5] *= 4  # quelques paires aberrantes (pont, sens unique) ne tirent pas la médiane
    r = calibrer_detour.fit(crow, road, current=1.35)
    assert r["paires"] == int((crow >= 0.2).sum())
    assert abs(r["facteur_median"] - 1.25) < 0.02
    assert r["erreur_moyenne_cale"] < r["erreur_moyenne_actuel"]
    assert r["biais_actuel"] > 0  # 1,35 surestime les km quand le vrai facteur est 1,25
