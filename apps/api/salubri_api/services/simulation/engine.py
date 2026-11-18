# SPDX-License-Identifier: AGPL-3.0-or-later
"""Daily multi-agent simulation of the collection chain.

Flows use expected values (smooth, comparable between scenarios); randomness only drives truck breakdowns,
so a given seed always gives the same result. Each îlot keeps two stocks, subscribed and non-subscribed
households, so the pre-collector only takes its clients' waste (the expected value of the agent model,
services/simulation/abm, docs/SIMULATION_ODD.md § 8). Mass balance holds exactly:
produced = trucks to landfill + municipal cleanup to landfill + wild stock + household stock + point levels.
"""

import time
from dataclasses import dataclass

import numpy as np

from salubri_api.services.simulation.agents import (
    IlotsState,
    PlanSnapshot,
    Precollector,
    WildDumps,
    schedule_days,
)
from salubri_api.services.simulation.metrics import Recorder
from salubri_api.services.simulation.params import SimParams


@dataclass
class SimResult:
    daily: dict[str, list[float]]
    summary: dict[str, float]
    duration_ms: int
    # stock final de chaque dépôt sauvage (kg) : sert au calage (taille des dépôts), jamais renvoyé par l'API
    wild_final_kg: np.ndarray | None = None


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def simulate(plan: PlanSnapshot, sp: SimParams, seed: int = 42) -> SimResult:
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)
    n = len(plan.ilot_population)
    n_pts = len(plan.point_capacity_kg)
    il = IlotsState(
        population=plan.ilot_population.astype(float) * sp.population_factor,
        subscribed=np.full(n, sp.subscription_rate),
        stock_kg=np.zeros(n),
        dist_m=plan.ilot_dist_m.astype(float),
        point=plan.ilot_point.astype(int),
        passes_planned=np.zeros(n),
        passes_done=np.zeros(n),
    )
    gen_kg = il.population * sp.kg_per_person_day * (1 + (sp.rain_waste_factor if sp.rain else 0.0))
    pc_days = schedule_days(sp.precollector_frequency_per_week)
    order = np.argsort(il.point, kind="stable")  # neighbouring ilots share a pre-collector
    collectors = [
        Precollector(
            order[i : i + sp.ilots_per_precollector], sp.precollector_capacity_kg, pc_days, sp.precollector_cost_month
        )
        for i in range(0, n, sp.ilots_per_precollector)
    ]
    level = np.zeros(n_pts)
    cap = plan.point_capacity_kg.astype(float)
    pickup_days = schedule_days(sp.pickup_frequency_per_week, sp.work_days_per_week)
    # wild dump locations: 0..n-1 near ilots, n..n+n_pts-1 next to collection points
    wild = WildDumps(
        kg=np.zeros(n + n_pts),
        age=np.zeros(n + n_pts),
        cleaned_day=np.full(n + n_pts, -1),
        near_water=np.concatenate([plan.ilot_near_water.astype(bool), np.zeros(n_pts, bool)]),
        recurring=np.zeros(n + n_pts, bool),
    )
    rec = Recorder()
    budget_left = sp.budget_month
    to_cet = cleanup_total = produced_total = 0.0
    watch_until = np.full(n, -1)  # Laabal: îlot sous effet dissuasif jusqu'à ce jour
    laabal_acc = 0.0
    reachable = il.dist_m <= sp.walk_distance_max_m
    last_pass = np.full(n, -99)

    def add_wild(loc: np.ndarray | int, kg: np.ndarray | float, day: int) -> None:
        idx = np.atleast_1d(loc)
        amt = np.broadcast_to(np.asarray(kg, dtype=float), idx.shape)
        for i, a in zip(idx, amt, strict=True):
            if a <= 0:
                continue
            if wild.kg[i] <= 1e-9:
                wild.age[i] = 0
                if wild.cleaned_day[i] >= 0 and day - wild.cleaned_day[i] <= sp.recurring_days:
                    wild.recurring[i] = True
            wild.kg[i] += a

    # Laabal : les riverains portent le dépotoir au point sans prendre la place des dépôts d'un jour normal
    inflow_day = np.bincount(il.point, gen_kg, minlength=n_pts)
    stock_s = np.zeros(n)  # part des abonnés ; il.stock_kg = abonnés + non-abonnés

    def resubscribe(new: np.ndarray) -> None:
        """Les ménages qui changent d'abonnement gardent leurs déchets : on déplace la part correspondante."""
        nonlocal stock_s
        old = il.subscribed
        stock_u = il.stock_kg - stock_s
        up = np.divide(new - old, 1 - old, out=np.zeros(n), where=(new > old) & (old < 1))
        down = np.divide(old - new, old, out=np.zeros(n), where=(new < old) & (old > 0))
        stock_s = stock_s + up * stock_u - down * stock_s
        il.subscribed = new

    for day in range(sp.horizon_days):
        dow = day % 7
        # 1. generation
        il.stock_kg += gen_kg
        stock_s += gen_kg * il.subscribed
        produced_total += float(gen_kg.sum())
        wild_new = precollected = voluntary = 0.0

        # 2. pre-collection (subscribed share)
        for pc in collectors:
            if dow not in pc.days:
                continue
            il.passes_planned[pc.ilots] += 1
            if not pc.active:
                continue
            room = pc.capacity_kg
            for i in pc.ilots:
                take = min(stock_s[i], room)
                if take <= 0:
                    continue
                room -= take
                il.stock_kg[i] -= take
                stock_s[i] -= take
                il.passes_done[i] += 1
                last_pass[i] = day
                p = il.point[i]
                into_point = min(take, max(cap[p] - level[p], 0.0))
                level[p] += into_point
                precollected += take
                if take - into_point > 0:  # point full: dumped next to it
                    add_wild(n + p, take - into_point, day)
                    wild_new += take - into_point
                if room <= 0:
                    break

        # 3. non-subscribed households (and subscribers who gave up waiting: stock above sub_wait_days)
        stock_s = np.minimum(stock_s, sp.sub_wait_days * gen_kg * il.subscribed)
        unsub = il.stock_kg - stock_s
        full = level[il.point] >= cap[il.point] - 1e-6
        can_bring = reachable & ~full
        for i in np.where(can_bring & (unsub > 0))[0]:
            p = il.point[i]
            moved = min(unsub[i], max(cap[p] - level[p], 0.0))
            level[p] += moved
            il.stock_kg[i] -= moved
            voluntary += moved
        far = ~can_bring & (unsub > 0)
        if far.any():
            excess = np.maximum(il.dist_m[far] - sp.walk_distance_max_m, 0)
            prob = _sigmoid(sp.p0 + sp.slope_dist * excess + sp.slope_full * full[far] + sp.slope_rain * sp.rain)
            prob = prob * (1 - sp.laabal_deterrence * (watch_until[far] >= day))
            dumped = unsub[far] * prob
            il.stock_kg[far] -= dumped
            add_wild(np.where(far)[0], dumped, day)
            wild_new += float(dumped.sum())

        # 4. municipal trucks
        km_today = cost_today = trucked = 0.0
        if dow in pickup_days:
            broken = {r.vehicle_idx for r in plan.routes if rng.random() < sp.breakdown_rate}
            for r in plan.routes:
                if r.vehicle_idx in broken or budget_left <= 0:
                    continue
                room = r.capacity_kg
                for p in r.points:
                    take = min(level[p], room)
                    level[p] -= take
                    room -= take
                    trucked += take
                km_today += r.distance_km
                c = r.distance_km * sp.fuel_cost_per_km + r.fixed_cost
                cost_today += c
                budget_left -= c
        to_cet += trucked

        # 5. point overflow indicator
        overflow = int((level >= cap - 1e-6).sum())

        # 6a. Brigade Laabal (police civique): descentes ciblées sur les îlots les plus sales.
        #     Pas de ramassage : les riverains sont contraints de nettoyer (déchets portés au point de regroupement
        #     du ménage, en laissant la place d'un jour de dépôts ; le reste attend l'équipe de nettoyage), de s'abonner, et l'effet dissuasif dure laabal_watch_days.
        active = wild.kg > 1e-6
        wild.age[active] += 1
        laabal_acc += sp.laabal_operations_per_week / 7
        ops = int(laabal_acc)
        laabal_acc -= ops
        controlled = 0
        returned = 0.0
        if ops:
            score = wild.kg[:n] + 500.0 * wild.recurring[:n] + 1e-3 * il.dist_m
            score[watch_until >= day] = -1
            targets = [i for i in np.argsort(-score)[: ops * sp.laabal_ilots_per_operation] if score[i] >= 0]
            for i in targets:
                watch_until[i] = day + sp.laabal_watch_days
                new = il.subscribed.copy()
                new[i] = min(1.0, new[i] + sp.laabal_sub_boost)
                resubscribe(new)
                if wild.kg[i] > 1e-6:  # riverains contraints d'évacuer vers leur point de regroupement
                    p = il.point[i]
                    moved = min(wild.kg[i], max(cap[p] - level[p] - inflow_day[p], 0.0))
                    level[p] += moved
                    wild.kg[i] -= moved
                    returned += moved
                    if wild.kg[i] <= 1e-6:
                        wild.kg[i] = 0.0
                        rec.cleanup_delays.append(int(wild.age[i]))
                        wild.cleaned_day[i] = day
            controlled = len(targets)

        # 6b. Services techniques de la mairie: nettoyage des dépotoirs, par priorité.
        prio = wild.kg * np.where(wild.near_water, 1.5, 1.0) * (1 + wild.age / 30)
        room = sp.cleanup_capacity_kg_day
        cleaned = 0.0
        for i in np.argsort(-prio):
            if room <= 0 or wild.kg[i] <= 1e-6:
                break
            take = min(wild.kg[i], room)
            wild.kg[i] -= take
            room -= take
            cleaned += take
            if wild.kg[i] <= 1e-6:
                wild.kg[i] = 0.0
                rec.cleanup_delays.append(int(wild.age[i]))
                wild.cleaned_day[i] = day
        cleanup_total += cleaned

        # 7. monthly: pre-collector economics, subscriptions, budget
        if day % 30 == 29:
            for pc in collectors:
                if not pc.active:
                    continue
                revenue = (
                    float((il.population[pc.ilots] / sp.household_size * il.subscribed[pc.ilots]).sum())
                    * sp.fee_fcfa_month
                )
                pc.months_in_loss = pc.months_in_loss + 1 if revenue < pc.cost_month else 0
                if pc.months_in_loss >= 2:
                    pc.active = False
                    rec.precollectors_dropped += 1
            regularity = np.divide(il.passes_done, il.passes_planned, out=np.zeros(n), where=il.passes_planned > 0)
            resubscribe(
                np.clip(
                    np.where(regularity >= sp.regularity_ok, il.subscribed + sp.sub_up, il.subscribed - sp.sub_down),
                    0,
                    1,
                )
            )
            il.passes_planned[:] = 0
            il.passes_done[:] = 0
            budget_left = sp.budget_month

        served = (day - last_pass <= 7) | (reachable & ~(level[il.point] >= cap[il.point] - 1e-6))
        pop = il.population.sum()
        rec.push(
            produced_t=gen_kg.sum() / 1000,
            precollected_t=precollected / 1000,
            voluntary_t=voluntary / 1000,
            truck_collected_t=trucked / 1000,
            wild_new_t=wild_new / 1000,
            wild_stock_t=wild.kg.sum() / 1000,
            wild_dumps_active=int((wild.kg > 50).sum()),
            cleanup_t=cleaned / 1000,
            laabal_controls=controlled,
            laabal_cleared_t=returned / 1000,
            overflow_points=overflow,
            truck_km=km_today,
            cost_fcfa=cost_today,
            household_stock_t=il.stock_kg.sum() / 1000,
            coverage_rate=float((il.population * served).sum() / pop) if pop else 0.0,
            subscription_rate=float((il.population * il.subscribed).sum() / pop) if pop else 0.0,
        )

    remaining = to_cet + cleanup_total + wild.kg.sum() + il.stock_kg.sum() + level.sum()
    err = abs(produced_total - remaining) / max(produced_total, 1.0)
    summary = rec.summary(mass_error=float(err), recurring=int(wild.recurring.sum()))
    return SimResult(dict(rec.daily), summary, int((time.perf_counter() - t0) * 1000), wild.kg.copy())


def run(plan: PlanSnapshot, sp: SimParams, seed: int, mode: str = "agrege") -> SimResult:
    """Une simulation : modèle à agents (`agents`) ou agrégé (`agrege`)."""
    if mode == "agents":
        from salubri_api.services.simulation.abm.model import simulate_agents

        return simulate_agents(plan, sp, seed)
    return simulate(plan, sp, seed)


QUANTILES = {"p5": 5, "p10": 10, "p90": 90, "p95": 95}  # p5–p95 = intervalle à 90 % ; p10–p90 gardés (compatibilité)


# Paramètres non calés dont l'incertitude est propagée (revue r7, F4) : (nom, tirage, bornes, source).
# « fois » : multiplie la valeur du scénario (log-uniforme pour une pente) ; « plus » : ajoute à la valeur.
UNCERTAIN: list[tuple[str, str, tuple[float, float], str]] = [
    ("kg_per_person_day", "fois", (0.75, 1.25), "0,6 kg annoncé par la mairie, jamais pesé ; ±25 %"),
    ("p0", "plus", (-1.0, 1.0), "propension de base à jeter, non calée (SIMULATION_CALIBRATION.md)"),
    ("slope_dist", "fois_log", (0.5, 2.0), "effet de la distance, non calé ; de la moitié au double"),
]


def draw_params(sp: SimParams, rng: np.random.Generator) -> SimParams:
    """Un jeu de paramètres incertains tiré dans leurs bornes documentées (UNCERTAIN)."""
    from dataclasses import replace

    kw: dict[str, float] = {}
    for name, how, (lo, hi), _ in UNCERTAIN:
        v = float(getattr(sp, name))
        if how == "fois":
            kw[name] = v * rng.uniform(lo, hi)
        elif how == "fois_log":
            kw[name] = v * float(np.exp(rng.uniform(np.log(lo), np.log(hi))))
        else:
            kw[name] = v + rng.uniform(lo, hi)
    return replace(sp, **kw)


def replicate(
    plan: PlanSnapshot, sp: SimParams, seed: int, n: int, mode: str = "agrege", uncertainty: bool = False
) -> dict[str, object]:
    """Run n seeds; return median and quantiles (p5, p10, p90, p95) per summary indicator and daily series.

    Avec `uncertainty`, n simulations de plus où les paramètres non calés (UNCERTAIN) sont tirés à chaque
    réplication : chaque indicateur reçoit aussi `median_param`, `p5_param`, `p95_param` (bruit + paramètres).
    Les mêmes graines servent aux deux séries : les écarts entre scénarios restent comparables."""
    runs = [run(plan, sp, seed + k, mode) for k in range(n)]
    summ = {}
    for k in runs[0].summary:
        v = np.array([r.summary[k] for r in runs], dtype=float)
        summ[k] = {"median": float(np.median(v)), **{q: float(np.percentile(v, x)) for q, x in QUANTILES.items()}}
    if uncertainty:
        rng = np.random.default_rng(seed + 100_003)
        pruns = [run(plan, draw_params(sp, rng), seed + k, mode) for k in range(n)]
        for k in summ:
            v = np.array([r.summary[k] for r in pruns], dtype=float)
            summ[k].update({"median_param": float(np.median(v)), "p5_param": float(np.percentile(v, 5)),
                            "p95_param": float(np.percentile(v, 95))})  # fmt: skip
    daily = {}
    for k in runs[0].daily:
        arr = np.array([r.daily[k] for r in runs])
        daily[k] = {
            "median": np.median(arr, axis=0).round(4).tolist(),
            **{q: np.percentile(arr, x, axis=0).round(4).tolist() for q, x in QUANTILES.items()},
        }
    return {
        "summary": summ,
        "daily": daily,
        "replications": n,
        "mode": mode,
        "duration_ms": sum(r.duration_ms for r in runs),
    }
