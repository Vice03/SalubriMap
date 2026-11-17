# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mesures de cohérence entre deux versions de plan (E7)."""

from salubri_api.services.plan.diff import PlanView, coherence, diff_plans

M = 1 / 111_320  # ~1 m en degrés de latitude


def view(points, routes=(), km=10.0, cost=1000.0, cov=0.9):  # type: ignore[no-untyped-def]
    return PlanView(points, set(routes), km, cost, 0, cov)


OLD = view(
    {"P1": (0.0, 0.0), "P2": (0.0, 100 * M), "P3": (0.0, 200 * M), "P4": (0.0, 300 * M)},
    [("BF-01", 1, ("P1", "P2")), ("BF-02", 1, ("P3", "P4"))],
)


def test_rien_ne_bouge() -> None:
    c = coherence(OLD, OLD)
    assert c["points_inchanges_part"] == 1 and c["deplacement_max_m"] == 0 and c["tournees_jaccard"] == 1
    assert diff_plans(OLD, OLD)["coherence"]["cout_delta"] == 0


def test_deplacement_et_remplacement() -> None:
    new = view(
        {"P1": (0.0, 0.0), "P2": (0.0, 130 * M), "P3": (0.0, 200 * M), "P5": (0.0, 350 * M)},
        [("BF-01", 1, ("P1", "P2")), ("BF-01", 2, ("P3", "P5"))],
        km=12,
        cost=1300,
        cov=0.95,
    )
    c = coherence(OLD, new)
    assert c["points_inchanges_part"] == 0.5  # P1, P3
    assert abs(c["deplacement_max_m"] - 50) < 1  # P4 remplacé par P5, 50 m plus loin
    assert abs(c["deplacement_moyen_m"] - 40) < 1  # (30 + 50) / 2
    # paires (camion, point) : {BF-01:P1, BF-01:P2} communes sur 6 distinctes
    assert c["tournees_jaccard"] == round(2 / 6, 3)
    assert c["cout_delta"] == 300 and c["km_delta"] == 2.0
    assert (c["couverture_avant"], c["couverture_apres"]) == (0.9, 0.95)


def test_premiere_version_sans_coherence() -> None:
    assert diff_plans(None, OLD)["coherence"] is None
