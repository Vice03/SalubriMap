# SPDX-License-Identifier: AGPL-3.0-or-later
"""Simulation constants derived from ScenarioParams (behavioural slopes are documented in docs/HYPOTHESES.md)."""

from dataclasses import dataclass

from salubri_api.services.params import ScenarioParams

INT_FIELDS = {"ilots_per_precollector", "recurring_days", "laabal_ilots_per_operation", "laabal_watch_days"}


@dataclass(frozen=True)
class SimParams:
    horizon_days: int
    kg_per_person_day: float
    population_factor: float
    rain: bool
    subscription_rate: float
    fee_fcfa_month: float
    precollector_capacity_kg: float
    precollector_frequency_per_week: float
    precollector_cost_month: float
    point_capacity_kg: float
    pickup_frequency_per_week: float
    walk_distance_max_m: float
    breakdown_rate: float
    budget_month: float
    fuel_cost_per_km: float
    cleanup_capacity_kg_day: float
    laabal_operations_per_week: float
    laabal_deterrence: float
    household_size: float = 7.0
    ilots_per_precollector: int = 15
    p0: float = -1.5  # baseline log-odds of dumping when the point is out of reach
    slope_dist: float = 0.004  # per metre beyond the walking distance
    slope_full: float = 0.5
    slope_rain: float = 0.3
    rain_waste_factor: float = 0.15
    sub_up: float = 0.02
    sub_down: float = 0.03
    regularity_ok: float = 0.8
    recurring_days: int = 15
    sub_wait_days: float = (
        4.0  # un abonné attend son pré-collecteur tant que son stock reste sous 4 jours de production
    )
    laabal_ilots_per_operation: int = 6  # îlots inspectés par opération (descente de quartier)
    laabal_watch_days: int = 21  # durée de l'effet dissuasif après un contrôle
    laabal_sub_boost: float = 0.05  # ménages contraints de s'abonner à la pré-collecte après contrôle
    abm: tuple[tuple[str, float], ...] = ()  # paramètres du modèle à agents (AbmParams) venus du fichier

    @staticmethod
    def from_scenario(p: ScenarioParams) -> "SimParams":
        """Paramètres du scénario + paramètres de comportement du fichier (`comportement` dans params_default.json,
        documentés dans params_schema.json) : ceux de ce dataclass et ceux du modèle à agents."""
        from dataclasses import MISSING, fields

        from salubri_api.services.simulation.abm.params import AbmParams

        beh = dict(p.comportement or {})
        own = {f.name for f in fields(SimParams) if f.default is not MISSING} - {"abm"}  # comportement seulement
        abm_names = {f.name for f in fields(AbmParams)}
        sim_kw = {k: (int(v) if k in INT_FIELDS else float(v)) for k, v in beh.items() if k in own}
        abm_kw = tuple(sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in beh.items() if k in abm_names))
        return SimParams(
            **sim_kw,
            abm=abm_kw,
            horizon_days=p.horizon_days,
            kg_per_person_day=p.waste_kg_per_person_day,
            population_factor=p.population_factor,
            rain=p.season == "rain",
            subscription_rate=p.subscription_rate,
            fee_fcfa_month=p.subscription_fee_fcfa_month,
            precollector_capacity_kg=p.precollector_capacity_t * 1000,
            precollector_frequency_per_week=p.precollector_frequency_per_week,
            precollector_cost_month=p.precollector_cost_fcfa_month,
            point_capacity_kg=p.collection_point_capacity_t * 1000,
            pickup_frequency_per_week=p.pickup_frequency_per_week,
            walk_distance_max_m=p.walk_distance_max_m,
            breakdown_rate=p.truck_breakdown_rate_per_day,
            budget_month=p.budget_fcfa_month,
            fuel_cost_per_km=p.fuel_cost_fcfa_per_km,
            cleanup_capacity_kg_day=p.cleanup_capacity_t_day * 1000,
            laabal_operations_per_week=p.laabal_operations_per_week,
            laabal_deterrence=p.laabal_deterrence,
        )
