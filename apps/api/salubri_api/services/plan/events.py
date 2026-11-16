# SPDX-License-Identifier: AGPL-3.0-or-later
"""Which pipeline stages an event invalidates. Stages whose input key did not change are reused (cache)."""

STAGES = [
    ("E1", "consolidate_reports", "Consolidation des signalements"),
    ("E2", "compute_demand", "Demande par îlot"),
    ("E3", "place_points", "Points de regroupement"),
    ("E4", "distance_matrix", "Matrice des distances"),
    ("E5", "solve_vrp", "Tournées"),
    ("E6", "quick_simulation", "Simulation 90 jours"),
    ("E7", "diff_with_previous", "Différences"),
]

INVALIDATES: dict[str, set[str]] = {
    "reports_changed": {"E1", "E7"},
    "fleet_changed": {"E5", "E6", "E7"},
    "season_changed": {"E2", "E4", "E5", "E6", "E7"},
    "zone_changed": {"E2", "E3", "E4", "E5", "E6", "E7"},
    "budget_changed": {"E6", "E7"},
    "frequency_changed": {"E3", "E4", "E5", "E6", "E7"},
    "subscription_changed": {"E6", "E7"},
    "manual": {s[0] for s in STAGES},
}

# zone_changed re-places only the points needed by new areas: existing points stay frozen.
INCREMENTAL_POINTS = {"zone_changed"}
