# SPDX-License-Identifier: AGPL-3.0-or-later
"""Modèle à agents de la filière déchets (docs/SIMULATION_ODD.md).

Un agent par ménage (tableaux NumPy, un élément par ménage), un par pré-collecteur ; la brigade Laabal et la
mairie sont des agents collectifs ; points de regroupement et dépotoirs sont passifs. Même ordonnancement
quotidien que le modèle agrégé (`engine.py`), dont il reprend les paramètres pour rester comparable. Un seul
générateur aléatoire, tiré dans un ordre fixe : même graine → même résultat. Bilan de masse exact.
"""

import time

import numpy as np

from salubri_api.services.simulation.abm.params import AbmParams
from salubri_api.services.simulation.agents import PlanSnapshot, schedule_days
from salubri_api.services.simulation.engine import SimResult
from salubri_api.services.simulation.metrics import DAILY_KEYS, Recorder
from salubri_api.services.simulation.params import SimParams

ABM_KEYS = [
    *DAILY_KEYS,
    "precollectors_active",
    "precollector_income_fcfa",
    "budget_left_fcfa",
    "laabal_fines",
    "households_dumping",
]
GARDER, PORTER, JETER = 0, 1, 2


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _fill(groups: np.ndarray, amounts: np.ndarray, room: np.ndarray) -> np.ndarray:
    """Part acceptée de chaque quantité, servie dans l'ordre donné, dans la limite de `room[groupe]`."""
    if len(amounts) == 0:
        return amounts.copy()
    order = np.argsort(groups, kind="stable")
    g, a = groups[order], amounts[order]
    cum = np.cumsum(a)
    start = np.r_[0, np.flatnonzero(np.diff(g)) + 1]
    offset = np.repeat(cum[start] - a[start], np.diff(np.r_[start, len(a)]))
    before = cum - a - offset
    acc = np.clip(room[g] - before, 0.0, a)
    out = np.empty_like(acc)
    out[order] = acc
    return out


def abm_params(sp: SimParams) -> AbmParams:
    """AbmParams du fichier de paramètres (sp.abm), défauts du code pour le reste."""
    kw: dict[str, object] = {}
    for k, v in sp.abm:
        cur = getattr(AbmParams(), k)
        kw[k] = tuple(v) if isinstance(cur, tuple) else (bool(v) if isinstance(cur, bool) else float(v))
    return AbmParams(**kw)  # type: ignore[arg-type]


def households_count(plan: PlanSnapshot, sp: SimParams) -> int:
    pop = plan.ilot_population.astype(float) * sp.population_factor
    return int(np.where(pop > 0, np.maximum(1, np.rint(pop / sp.household_size)), 0).sum())


def simulate_agents(plan: PlanSnapshot, sp: SimParams, seed: int = 42, ap: AbmParams | None = None) -> SimResult:
    ap = ap or abm_params(sp)
    het = ap.heterogeneite
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)
    n, n_pts = len(plan.ilot_population), len(plan.point_capacity_kg)
    pop_il = plan.ilot_population.astype(float) * sp.population_factor
    dist_il = plan.ilot_dist_m.astype(float)
    point_il = plan.ilot_point.astype(int)

    # --- ménages (ODD § 2 et § 5) ---
    nh_il = np.where(pop_il > 0, np.maximum(1, np.rint(pop_il / sp.household_size)), 0).astype(int)
    hh_ilot = np.repeat(np.arange(n), nh_il)
    h = len(hh_ilot)
    if het:
        size = 1.0 + rng.poisson(sp.household_size - 1, h)
        size *= (pop_il / np.maximum(np.bincount(hh_ilot, size, minlength=n), 1e-9))[hh_ilot]  # population exacte
        income = rng.choice(3, size=h, p=ap.revenu_parts)
        sig = ap.sigma_production
        fprod = rng.lognormal(-sig * sig / 2, sig, h)
        dist = np.maximum(dist_il[hh_ilot] + rng.uniform(-ap.jitter_distance_m, ap.jitter_distance_m, h), 0.0)
    else:
        size = (pop_il / np.maximum(nh_il, 1))[hh_ilot]
        income = np.ones(h, int)
        fprod = np.ones(h)
        dist = dist_il[hh_ilot].copy()
    point_h = point_il[hh_ilot]
    sub = rng.random(h) < sp.subscription_rate
    prod_h = size * sp.kg_per_person_day * fprod * (1 + (sp.rain_waste_factor if sp.rain else 0.0))
    stock = np.zeros(h)
    habit = np.full(h, GARDER)
    dumped_day = np.full(h, -99)
    last_pass = np.full(h, -99)
    planned7, done7 = np.zeros((7, h), bool), np.zeros((7, h), bool)
    planned_m, done_m = np.zeros(h), np.zeros(h)
    inflow_day = np.bincount(point_h, prod_h, minlength=n_pts)  # dépôts d'un jour normal à chaque point
    reachable = dist <= sp.walk_distance_max_m
    excess = np.maximum(dist - sp.walk_distance_max_m, 0.0)
    revenu = np.asarray(ap.revenu_fcfa_mois)[income]
    nh_safe = np.maximum(nh_il, 1)

    # --- pré-collecteurs : 15 îlots voisins chacun, comme le modèle agrégé ---
    order = np.argsort(point_il, kind="stable")
    rank = np.empty(n, int)
    rank[order] = np.arange(n)
    ilot_coll = rank // sp.ilots_per_precollector
    n_coll = int(ilot_coll.max()) + 1 if n else 0
    coll_active = np.ones(n_coll, bool)
    months_loss = np.zeros(n_coll, int)
    load_sum, load_n = np.zeros(n_coll), np.zeros(n_coll)
    income_mean = 0.0
    hh_sorted = np.argsort(rank[hh_ilot], kind="stable")
    pc_days = schedule_days(sp.precollector_frequency_per_week)
    pc_room = np.full(n_coll, sp.precollector_capacity_kg)

    # --- points, dépotoirs (0..n-1 près des îlots, n.. à côté des points), mairie, brigade ---
    cap = plan.point_capacity_kg.astype(float)
    level = np.zeros(n_pts)
    wild_kg, wild_age = np.zeros(n + n_pts), np.zeros(n + n_pts)
    cleaned_day = np.full(n + n_pts, -1)
    recurring = np.zeros(n + n_pts, bool)
    near_water = np.concatenate([plan.ilot_near_water.astype(bool), np.zeros(n_pts, bool)])
    pickup_days = schedule_days(sp.pickup_frequency_per_week)
    budget_left = sp.budget_month
    watch_until = np.full(n, -1)
    laabal_acc = 0.0
    ln_det = np.log(1 - min(sp.laabal_deterrence, 0.999))
    beta_norme = ap.beta_norme if het else 0.0
    beta_hab = ap.beta_habitude if het else 0.0
    beta_dist_porter = ap.beta_dist_porter if het else 0.0

    rec = Recorder(ABM_KEYS)
    to_cet = cleanup_total = produced_total = 0.0

    def add_wild(amt: np.ndarray, day: int) -> None:
        new = (amt > 0) & (wild_kg <= 1e-9)
        wild_age[new] = 0
        recurring[new & (cleaned_day >= 0) & (day - cleaned_day <= sp.recurring_days)] = True
        wild_kg[:] += amt

    def cleaned(i: np.ndarray, day: int) -> None:
        done = i[wild_kg[i] <= 1e-6]
        wild_kg[done] = 0.0
        rec.cleanup_delays.extend(int(a) for a in wild_age[done])
        cleaned_day[done] = day

    for day in range(sp.horizon_days):
        dow, slot = day % 7, day % 7
        planned7[slot], done7[slot] = False, False

        # 1. production
        stock += prod_h
        produced_total += float(prod_h.sum())
        wild_new = precollected = voluntary = 0.0

        # 2. pré-collecte
        if dow in pc_days:
            planned7[slot] |= sub
            planned_m += sub
            act = sub & coll_active[ilot_coll[hh_ilot]]
            idx = hh_sorted[act[hh_sorted]]
            cid = ilot_coll[hh_ilot[idx]]
            before = stock[idx]
            take = _fill(cid, before, pc_room)
            stock[idx] -= take
            served = idx[(take > 0) | (before <= 1e-9)]
            last_pass[served] = day
            done7[slot, served] = True
            done_m[served] += 1
            on_duty = coll_active.copy()
            load_sum += np.bincount(cid, take, minlength=n_coll) / sp.precollector_capacity_kg * on_duty
            load_n += on_duty
            total = np.bincount(point_h[idx], take, minlength=n_pts)
            into = np.minimum(total, np.maximum(cap - level, 0.0))
            level += into
            over = np.concatenate([np.zeros(n), total - into])
            add_wild(over, day)
            wild_new += float(over.sum())
            precollected = float(take.sum())

        # 3. choix des ménages (logit multinomial, ODD § 7.1)
        full_pt = level >= cap - 1e-6
        # un abonné attend son pré-collecteur tant que son stock reste sous sub_wait_days de production
        decide = (stock > 1e-9) & (~sub | (stock > sp.sub_wait_days * prod_h))
        d = np.flatnonzero(decide)
        n_dumping = 0
        if len(d):
            pl, dn = planned7[:, d].sum(0), done7[:, d].sum(0)
            reg = np.where(pl > 0, dn / np.maximum(pl, 1), 1.0)
            share = np.bincount(hh_ilot, dumped_day >= day - 6, minlength=n) / nh_safe
            full_h = full_pt[point_h[d]]
            v_keep = ap.beta_reg * reg * sub[d] if het else np.zeros(len(d))
            v_carry = np.where(
                reachable[d] & ~full_h,
                ap.alpha_porter - beta_dist_porter * dist[d] / 100 + beta_hab * (habit[d] == PORTER),
                -np.inf,
            )
            il = hh_ilot[d]
            v_dump = (
                sp.p0
                + sp.slope_dist * excess[d]
                + sp.slope_full * full_h
                + sp.slope_rain * sp.rain
                + ln_det * (watch_until[il] >= day)
                + beta_norme * (share[il] - ap.norme_reference)
                + beta_hab * (habit[d] == JETER)
            )
            v = np.stack([v_keep, v_carry, v_dump])
            ev = np.exp(v - v.max(0))
            p = ev / ev.sum(0)
            u = rng.random(len(d))
            choice = (u >= p[0]).astype(int) + (u >= p[0] + p[1])
            habit[d] = choice
            c = d[choice == PORTER]
            acc = _fill(point_h[c], stock[c], np.maximum(cap - level, 0.0))
            level += np.bincount(point_h[c], acc, minlength=n_pts)
            stock[c] -= acc
            voluntary = float(acc.sum())
            j = d[choice == JETER]
            amt = np.concatenate([np.bincount(hh_ilot[j], stock[j], minlength=n), np.zeros(n_pts)])
            add_wild(amt, day)
            wild_new += float(stock[j].sum())
            stock[j] = 0.0
            dumped_day[j] = day
            n_dumping = len(j)

        # 4. camions de la mairie (identique au modèle agrégé)
        km_today = cost_today = trucked = 0.0
        if dow in pickup_days:
            broken = {r.vehicle_idx for r in plan.routes if rng.random() < sp.breakdown_rate}
            for r in plan.routes:
                if r.vehicle_idx in broken or budget_left <= 0:
                    continue
                room = r.capacity_kg
                for pt in r.points:
                    take_pt = min(level[pt], room)
                    level[pt] -= take_pt
                    room -= take_pt
                    trucked += take_pt
                km_today += r.distance_km
                cst = r.distance_km * sp.fuel_cost_per_km + r.fixed_cost
                cost_today += cst
                budget_left -= cst
        to_cet += trucked
        overflow = int((level >= cap - 1e-6).sum())

        # 5. brigade Laabal (ODD § 7.3)
        wild_age[wild_kg > 1e-6] += 1
        laabal_acc += sp.laabal_operations_per_week / 7
        ops = int(laabal_acc)
        laabal_acc -= ops
        controlled = fines = 0
        returned = 0.0
        if ops:
            score = wild_kg[:n] + 500.0 * recurring[:n] + 1e-3 * dist_il
            score[watch_until >= day] = -1
            targets = np.array(
                [i for i in np.argsort(-score)[: ops * sp.laabal_ilots_per_operation] if score[i] >= 0], int
            )
            if len(targets):
                watch_until[targets] = day + sp.laabal_watch_days
                is_t = np.zeros(n, bool)
                is_t[targets] = True
                in_t = is_t[hh_ilot]
                fines = int((in_t & (dumped_day >= day - 6)).sum())
                s_il = np.bincount(hh_ilot, sub, minlength=n) / nh_safe
                p_boost = np.minimum(1.0, sp.laabal_sub_boost / np.maximum(1 - s_il, 1e-9))[hh_ilot]
                u = rng.random(h)
                sub |= in_t & ~sub & (u < p_boost)
                dirty = targets[wild_kg[targets] > 1e-6]
                for i in dirty:  # riverains contraints de porter le dépotoir au point
                    pt = point_il[i]
                    moved = min(wild_kg[i], max(cap[pt] - level[pt] - inflow_day[pt], 0.0))
                    level[pt] += moved
                    wild_kg[i] -= moved
                    returned += moved
                cleaned(dirty, day)
            controlled = len(targets)

        # 6. nettoyage par la mairie (ODD § 7.4)
        prio = (
            wild_kg
            * np.where(near_water, 1.5, 1.0)
            * np.where(recurring, ap.priorite_recurrent, 1.0)
            * (1 + wild_age / 30)
        )
        room = sp.cleanup_capacity_kg_day
        cleaned_kg = 0.0
        touched = []
        for i in np.argsort(-prio):
            if room <= 0 or wild_kg[i] <= 1e-6:
                break
            take_w = min(wild_kg[i], room)
            wild_kg[i] -= take_w
            room -= take_w
            cleaned_kg += take_w
            touched.append(i)
        cleaned(np.array(touched, int), day)
        cleanup_total += cleaned_kg

        # 7. fin de mois : pré-collecteurs, abonnements, budget
        if day % 30 == 29:
            revenue = np.bincount(ilot_coll[hh_ilot[sub]], minlength=n_coll) * sp.fee_fcfa_month
            months_loss = np.where(coll_active & (revenue < sp.precollector_cost_month), months_loss + 1, 0)
            quit_ = coll_active & (months_loss >= 2)
            rec.precollectors_dropped += int(quit_.sum())
            coll_active &= ~quit_
            income_mean = float(revenue[coll_active].mean()) if coll_active.any() else 0.0
            if het:  # extension : un collecteur rentable et peu chargé reprend les îlots d'un voisin parti
                load = np.divide(load_sum, load_n, out=np.ones(n_coll), where=load_n > 0)
                orphan = [k for k in range(n_coll) if not coll_active[k] and (ilot_coll == k).any()]
                for c in np.flatnonzero(
                    coll_active
                    & (revenue >= ap.extension_marge * sp.precollector_cost_month)
                    & (load < ap.extension_charge_max)
                ):
                    if not orphan:
                        break
                    k = min(orphan, key=lambda o, c=c: abs(o - c))
                    orphan.remove(k)
                    ilot_coll[ilot_coll == k] = c
            served_il = coll_active[ilot_coll]
            pl_il = np.bincount(hh_ilot, planned_m * sub, minlength=n)
            reg_il = np.where(
                pl_il > 0, np.bincount(hh_ilot, done_m * sub, minlength=n) / np.maximum(pl_il, 1), served_il * 1.0
            )
            u = rng.random(h)
            if het:
                fee_share = sp.fee_fcfa_month / revenu
                p_in = _sigmoid(ap.a_abo + ap.beta_reg_mois * (reg_il[hh_ilot] - 0.8) - ap.beta_prix * fee_share)
                p_in *= served_il[hh_ilot]
                reg_p = np.where(planned_m > 0, done_m / np.maximum(planned_m, 1), 1.0)
                p_out = _sigmoid(ap.a_desabo - ap.beta_reg_mois * (reg_p - 0.8) + ap.beta_prix * fee_share)
            else:  # variations moyennes exactes du modèle agrégé (+sub_up / −sub_down par îlot)
                s_il = (np.bincount(hh_ilot, sub, minlength=n) / nh_safe)[hh_ilot]
                up = (reg_il >= sp.regularity_ok)[hh_ilot]
                p_in = np.where(up, np.minimum(1.0, sp.sub_up / np.maximum(1 - s_il, 1e-9)), 0.0)
                p_out = np.where(~up, np.minimum(1.0, sp.sub_down / np.maximum(s_il, 1e-9)), 0.0)
            sub = np.where(sub, u >= p_out, u < p_in)
            planned_m[:] = 0
            done_m[:] = 0
            load_sum[:] = 0
            load_n[:] = 0
            budget_left = sp.budget_month

        served_h = (sub & (day - last_pass <= 7)) | (reachable & ~(level >= cap - 1e-6)[point_h])
        pop = size.sum()
        rec.push(
            produced_t=prod_h.sum() / 1000,
            precollected_t=precollected / 1000,
            voluntary_t=voluntary / 1000,
            truck_collected_t=trucked / 1000,
            wild_new_t=wild_new / 1000,
            wild_stock_t=wild_kg.sum() / 1000,
            wild_dumps_active=int((wild_kg > 50).sum()),
            cleanup_t=cleaned_kg / 1000,
            laabal_controls=controlled,
            laabal_cleared_t=returned / 1000,
            overflow_points=overflow,
            truck_km=km_today,
            cost_fcfa=cost_today,
            household_stock_t=stock.sum() / 1000,
            coverage_rate=float((size * served_h).sum() / pop) if pop else 0.0,
            subscription_rate=float((size * sub).sum() / pop) if pop else 0.0,
            precollectors_active=int(coll_active.sum()),
            precollector_income_fcfa=income_mean,
            budget_left_fcfa=budget_left,
            laabal_fines=fines,
            households_dumping=n_dumping,
        )

    remaining = to_cet + cleanup_total + wild_kg.sum() + stock.sum() + level.sum()
    err = abs(produced_total - remaining) / max(produced_total, 1.0)
    summary = rec.summary(mass_error=float(err), recurring=int(recurring.sum()))
    dd = rec.daily
    summary.update(
        {
            "households": h,
            "precollectors_active_final": int(dd["precollectors_active"][-1]) if dd["precollectors_active"] else 0,
            "precollector_income_mean_fcfa": round(income_mean, 0),
            "budget_left_final_fcfa": round(budget_left, 0),
            "laabal_fines": int(sum(dd["laabal_fines"])),
            "voluntary_t": round(float(sum(dd["voluntary_t"])), 2),
        }
    )
    return SimResult(dict(rec.daily), summary, int((time.perf_counter() - t0) * 1000), wild_kg.copy())
