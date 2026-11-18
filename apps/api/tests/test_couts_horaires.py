# SPDX-License-Identifier: AGPL-3.0-or-later
"""Horaires réglables (8 h – 18 h, jours travaillés) et estimation des coûts."""

import pytest
from pydantic import ValidationError

from salubri_api.services import costs
from salubri_api.services.params import ScenarioParams
from salubri_api.services.simulation.agents import schedule_days


def test_jours_travailles():
    assert schedule_days(2, 6) == {0, 3}
    assert schedule_days(7, 6) == {0, 1, 2, 3, 4, 5}  # jamais le dimanche
    assert 6 not in schedule_days(3, 6)


def test_horaires_par_defaut_et_controle():
    p = ScenarioParams()
    assert p.shift_minutes == (480, 1020)  # 8 h – 18 h, 1 h de pause déduite
    with pytest.raises(ValidationError):
        ScenarioParams(work_start_h=17, work_end_h=18, break_min=30)


def test_estimation_couts():
    p = ScenarioParams(pickup_frequency_per_week=2)
    c = costs.estimate(p, km_day=100, trucks_fleet=2, trucks_used=2, points=10, demand_t_week=50)
    km = 100 * 2 * 52 / 12
    assert c["km_mois"] == round(km)
    assert c["mois_fcfa"]["carburant"] == round(km * 0.40 * 750)
    assert c["mois_fcfa"]["equipages"] == round(2 * (120_000 + 3 * 60_000) * 1.16)
    assert c["total_mois_fcfa"] == sum(c["mois_fcfa"].values())
    assert c["cout_par_tonne_fcfa"] == round(c["total_mois_fcfa"] / (50 * 52 / 12))
    assert c["horaires"] == {"debut": "08:00", "fin": "17:00", "pause_min": 60, "jours_semaine": 6}


def test_plan_donne_les_couts(client):  # type: ignore[no-untyped-def]
    from tests.test_scenarios_api import wait

    sc = client.get("/api/scenarios").json()[0]
    r = client.patch(f"/api/scenarios/{sc['id']}", json={"params": {"work_start_h": 7}}).json()
    assert r["event"] == "fleet_changed"
    plan = wait(client, r["plan_version_id"], 60)
    assert plan["status"] == "ready", plan.get("error")
    c = plan["summary"]["couts"]
    assert c["total_mois_fcfa"] > 0 and c["camions_flotte"] >= 1 and c["cout_km_fcfa"] == 420
