# SPDX-License-Identifier: AGPL-3.0-or-later
"""Daily series and summary indicators."""

from collections import defaultdict

import numpy as np

DAILY_KEYS = [
    "produced_t",
    "precollected_t",
    "voluntary_t",
    "truck_collected_t",
    "wild_new_t",
    "wild_stock_t",
    "wild_dumps_active",
    "cleanup_t",
    "laabal_controls",
    "laabal_cleared_t",
    "overflow_points",
    "truck_km",
    "cost_fcfa",
    "household_stock_t",
    "coverage_rate",
    "subscription_rate",
]


class Recorder:
    def __init__(self) -> None:
        self.daily: dict[str, list[float]] = defaultdict(list)
        self.cleanup_delays: list[int] = []
        self.precollectors_dropped = 0

    def push(self, **values: float) -> None:
        for k in DAILY_KEYS:
            self.daily[k].append(round(float(values.get(k, 0.0)), 4))

    def summary(self, mass_error: float, recurring: int) -> dict[str, float]:
        d = {k: np.array(v) for k, v in self.daily.items()}
        collected = float(d["truck_collected_t"].sum())
        cost = float(d["cost_fcfa"].sum())
        return {
            "produced_t": round(float(d["produced_t"].sum()), 2),
            "collected_t": round(collected, 2),
            "precollected_t": round(float(d["precollected_t"].sum()), 2),
            "wild_dump_t": round(float(d["wild_new_t"].sum()), 2),
            "wild_dumps_active_final": int(d["wild_dumps_active"][-1]) if len(d["wild_dumps_active"]) else 0,
            "wild_dumps_active_mean": round(float(d["wild_dumps_active"].mean()), 1)
            if len(d["wild_dumps_active"])
            else 0,
            "cleanup_t": round(float(d["cleanup_t"].sum()), 2),
            "laabal_controls": int(d["laabal_controls"].sum()),
            "laabal_cleared_t": round(float(d["laabal_cleared_t"].sum()), 2),
            "mean_cleanup_delay_days": round(float(np.mean(self.cleanup_delays)), 1) if self.cleanup_delays else 0.0,
            "overflow_point_days": int(d["overflow_points"].sum()),
            "truck_km": round(float(d["truck_km"].sum()), 1),
            "cost_total_fcfa": round(cost, 0),
            "cost_per_t": round(cost / collected, 0) if collected > 0 else 0.0,
            "coverage_rate": round(float(d["coverage_rate"].mean()), 3) if len(d["coverage_rate"]) else 0.0,
            "subscription_rate_final": float(d["subscription_rate"][-1]) if len(d["subscription_rate"]) else 0.0,
            "precollectors_dropped": self.precollectors_dropped,
            "recurring_dumps": recurring,
            "mass_balance_error": mass_error,
        }
