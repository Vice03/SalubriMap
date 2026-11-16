# SPDX-License-Identifier: AGPL-3.0-or-later
"""Recompute timings per event type on a scratch clone of the baseline scenario.

    python scripts/bench_pipeline.py [--api http://localhost] [--n 5]
Fails (exit 1) if a partial recompute p95 > 2 s or a full one > 5 s (server-side duration).
"""

import argparse
import os
import statistics
import sys
import time

import httpx

LIMITS = {"fleet": 2.0, "budget": 2.0, "subscription": 2.0, "season": 5.0, "manual": 5.0}


def wait(c: httpx.Client, pid: str) -> dict:  # type: ignore[type-arg]
    while True:
        p = c.get(f"/api/plans/{pid}").json()
        if p["status"] == "superseded":
            pid = c.get(f"/api/scenarios/{p['scenario_id']}").json()["latest_plan_id"]
        elif p["status"] in ("ready", "failed"):
            return p  # type: ignore[no-any-return]
        time.sleep(0.05)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost")
    ap.add_argument("--n", type=int, default=5)
    a = ap.parse_args()
    token = os.environ.get("SALUBRI_ADMIN_TOKEN", "ouaga2026")
    with httpx.Client(base_url=a.api, timeout=60, headers={"X-Salubri-Token": token}) as c:
        base = next(s for s in c.get("/api/scenarios").json() if s["is_baseline"])
        sc = c.post("/api/scenarios", json={"name": "Banc d'essai", "parent_id": base["id"]}).json()
        wait(c, sc["plan_version_id"])
        sid, v = sc["id"], sc["vehicles"][0]["id"]
        budget = sc["params"]["budget_fcfa_month"]
        timings: dict[str, list[float]] = {k: [] for k in LIMITS}
        for i in range(a.n):
            ops = {
                "fleet": lambda i=i: c.post(
                    f"/api/scenarios/{sid}/vehicles/{v}/breakdown", json={"out_of_service": i % 2 == 0}
                ),
                "budget": lambda i=i: c.patch(
                    f"/api/scenarios/{sid}", json={"params": {"budget_fcfa_month": budget * (0.7 + 0.01 * i)}}
                ),
                "subscription": lambda i=i: c.patch(
                    f"/api/scenarios/{sid}", json={"params": {"subscription_rate": 0.3 + 0.01 * i}}
                ),
                "season": lambda i=i: c.patch(
                    f"/api/scenarios/{sid}", json={"params": {"season": "rain" if i % 2 == 0 else "dry"}}
                ),
                "manual": lambda i=i: c.post(f"/api/scenarios/{sid}/recompute", json={"reason": "bench"}),
            }
            for kind, op in ops.items():
                body = op().json()
                pid = body.get("plan_version_id")
                p = wait(c, pid)
                timings[kind].append((p["summary"] or {}).get("duration_ms", 0) / 1000)
        c.delete(f"/api/scenarios/{sid}")
    bad = False
    print(f"{'événement':14} {'médiane':>8} {'p95':>8} {'limite':>7}")
    for kind, xs in timings.items():
        xs = sorted(xs)
        p95 = xs[min(len(xs) - 1, round(0.95 * (len(xs) - 1)))]
        over = p95 > LIMITS[kind]
        bad |= over
        print(f"{kind:14} {statistics.median(xs):7.2f}s {p95:7.2f}s {LIMITS[kind]:6.1f}s {'DÉPASSÉ' if over else 'ok'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
