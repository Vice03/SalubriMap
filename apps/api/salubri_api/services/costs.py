# SPDX-License-Identifier: AGPL-3.0-or-later
"""Estimation des coûts mensuels d'un plan : carburant, entretien, équipages, camions, bacs.

Tout vient des paramètres du scénario (valeurs par défaut sourcées dans docs/HYPOTHESES.md, toutes modifiables) et du
plan calculé (km d'une journée de collecte, camions, points). C'est une estimation : le budget réel de la mairie
reste la référence."""

from typing import Any

from salubri_api.services.params import ScenarioParams

WEEKS_PER_MONTH = 52 / 12


def estimate(
    p: ScenarioParams, km_day: float, trucks_fleet: int, trucks_used: int, points: int, demand_t_week: float
) -> dict[str, Any]:
    """`km_day` : km d'une journée de collecte (toutes tournées) ; une journée par enlèvement de la semaine."""
    days_week = min(p.pickup_frequency_per_week, p.work_days_per_week)
    km_month = km_day * days_week * WEEKS_PER_MONTH
    fuel_l = km_month * p.fuel_l_per_100km / 100
    crew = (p.driver_salary_fcfa_month + p.loaders_per_truck * p.loader_salary_fcfa_month) * (1 + p.social_charges_rate)
    lines = {
        "carburant": fuel_l * p.fuel_price_fcfa_l,
        "entretien": km_month * p.maintenance_fcfa_per_km,
        "equipages": crew * trucks_fleet,
        "amortissement_camions": trucks_fleet * p.truck_price_fcfa / p.truck_life_years / 12,
        "assurance_camions": trucks_fleet * p.truck_insurance_fcfa_year / 12,
        "amortissement_bacs": points * p.bin_price_fcfa / p.bin_life_years / 12,
    }
    total = sum(lines.values())
    tonnes = demand_t_week * WEEKS_PER_MONTH
    start, end = p.shift_minutes
    return {
        "mois_fcfa": {k: round(v) for k, v in lines.items()},
        "total_mois_fcfa": round(total),
        "total_an_fcfa": round(total * 12),
        "cout_par_tonne_fcfa": round(total / tonnes) if tonnes > 0 else None,
        "km_mois": round(km_month),
        "gasoil_litres_mois": round(fuel_l),
        "cout_km_fcfa": round(p.cost_per_km),
        "journees_collecte_semaine": days_week,
        "camions_flotte": trucks_fleet,
        "camions_utilises": trucks_used,
        "agents": trucks_fleet * (1 + p.loaders_per_truck),
        "horaires": {
            "debut": f"{start // 60:02d}:{start % 60:02d}",
            "fin": f"{end // 60:02d}:{end % 60:02d}",
            "pause_min": p.break_min,
            "jours_semaine": p.work_days_per_week,
        },  # fmt: skip
        "budget_mois_fcfa": round(p.budget_fcfa_month),
        "dans_le_budget": total <= p.budget_fcfa_month,
    }
