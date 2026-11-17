#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Plan d'un arrondissement : scénario restreint, 4 variantes simulées (modèle à agents, réplications), document.

    PYTHONPATH=apps/api python scripts/plan_arrondissement.py --arrondissement 9 --api http://localhost

Crée (ou réutilise) le scénario « Arrondissement N », calcule son plan, puis 4 variantes : référence, 2 camions en
panne, saison des pluies, abonnements +20 % ; pour chacune `--replications` simulations (30 par défaut). Écrit
docs/PLAN_ARRONDISSEMENT_<N>.md, docs/figures/plan_arr<N>_carte.svg et docs/figures/plan_arr<N>.json (résultats
bruts). PDF : scripts/md_pdf.sh docs/PLAN_ARRONDISSEMENT_<N>.md.
"""

import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
STAFF_PER_TRUCK = (1, 2)  # [H] un chauffeur, deux ripeurs par camion et par rotation (docs/PARAMETRES.md)


# Population des arrondissements, RGPH 2019 (INSD, monographie de la commune de Ouagadougou, août 2022, tableau 2.2)
POP_INSD_2019 = {9: 336_483}


def wait(c: httpx.Client, plan_id: str, timeout: float = 300) -> dict[str, Any]:
    t0 = time.time()
    while time.time() - t0 < timeout:
        p = c.get(f"/api/plans/{plan_id}").json()
        if p["status"] in ("ready", "failed"):
            if p["status"] == "failed":
                raise SystemExit(f"Plan en échec : {p.get('error')}")
            return p
        time.sleep(1)
    raise SystemExit("Plan trop long")


def simulate(c: httpx.Client, plan_id: str, n: int) -> dict[str, Any]:
    run = c.post(f"/api/plans/{plan_id}/simulate", json={"replications": n}).json()
    for _ in range(1200):
        out = c.get(f"/api/sim-runs/{run['sim_run_id']}").json()
        if out["status"] in ("ready", "failed"):
            return out
        time.sleep(1)
    raise SystemExit("Simulation trop longue")


def scenario(c: httpx.Client, name: str, parent: str, params: dict[str, Any]) -> str:
    for s in c.get("/api/scenarios").json():
        if s["name"] == name:
            c.delete(f"/api/scenarios/{s['id']}")
    sid = c.post("/api/scenarios", json={"name": name, "parent_id": parent}).json()["id"]
    pid = c.patch(f"/api/scenarios/{sid}", json={"params": params}).json()["plan_version_id"]
    wait(c, pid)
    return sid


def rings(geom: dict) -> list:  # type: ignore[type-arg]
    if geom["type"] == "Polygon":
        return list(geom["coordinates"])
    return [r for poly in geom["coordinates"] for r in poly]


def svg_map(points: list[dict], routes: list[dict], quartiers: list[dict]) -> str:  # type: ignore[type-arg]
    xs, ys = [], []
    for q in quartiers:
        for ring in rings(q["geometry"]):
            for x, y, *_ in ring:
                xs.append(x)
                ys.append(y)
    for p in points:
        xs.append(p["geometry"]["coordinates"][0])
        ys.append(p["geometry"]["coordinates"][1])
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    w, h = 900, 900 * (y1 - y0) / max(x1 - x0, 1e-9)

    def px(x: float, y: float) -> str:
        return f"{20 + (x - x0) / (x1 - x0) * w:.1f},{20 + (y1 - y) / (y1 - y0) * h:.1f}"

    colors = ["#c0392b", "#2471a3", "#1e8449", "#7d3c98", "#b9770e", "#148f77", "#566573", "#a04000"]
    vcol: dict[str, str] = {}
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w + 40:.0f}" height="{h + 70:.0f}" font-family="sans-serif">',
           '<rect width="100%" height="100%" fill="#fbfaf6"/>',
           f'<clipPath id="cadre"><rect x="0" y="0" width="{w + 40:.0f}" height="{h + 30:.0f}"/></clipPath>',
           '<g clip-path="url(#cadre)">']  # fmt: skip
    for q in quartiers:
        for ring in rings(q["geometry"]):
            out.append(f'<polygon points="{" ".join(px(c[0], c[1]) for c in ring)}" fill="#efe8d8" stroke="#9c8f74"/>')
    for r in routes:
        pr = r["properties"]
        col = vcol.setdefault(pr["vehicle_label"], colors[len(vcol) % len(colors)])
        g = r.get("geometry") or {}
        lines = g.get("coordinates", []) if g.get("type") == "MultiLineString" else [g.get("coordinates", [])]
        pts = " ".join(px(c[0], c[1]) for line in lines for c in line)
        if pts:
            dash = ' stroke-dasharray="6 4"' if pr["rotation"] > 1 else ""
            out.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.5"{dash} opacity=".85"/>')
    for p in points:
        x, y = p["geometry"]["coordinates"]
        fill = "#555" if p["properties"].get("frozen") else "#111"
        cx, cy = px(x, y).split(",")
        out.append(f'<circle cx="{cx}" cy="{cy}" r="4.5" fill="{fill}" stroke="#fff" stroke-width="1.5"/>')
    out.append("</g>")
    ly = h + 45
    for i, (lab, col) in enumerate(vcol.items()):
        out.append(
            f'<line x1="{20 + i * 110}" y1="{ly}" x2="{50 + i * 110}" y2="{ly}" stroke="{col}" stroke-width="3"/>'
        )
        out.append(f'<text x="{55 + i * 110}" y="{ly + 4}" font-size="13">{lab}</text>')
    out.append(f'<text x="20" y="{ly + 22}" font-size="12" fill="#444">● point de regroupement · trait plein : '
               "1re rotation, pointillé : 2e rotation · les traits qui sortent du cadre vont au dépôt ou à la décharge</text></svg>")  # fmt: skip
    return "\n".join(out)


def hm(m: float) -> str:
    return f"{int(m // 60):02d}:{int(m % 60):02d}"


def n(x: float, d: int = 1) -> str:
    return f"{x:,.{d}f}".replace(",", " ").replace(".", ",")


def iv(s: dict[str, Any], k: str, d: int = 1, f: float = 1.0) -> str:
    v = s.get(k)
    if not v:
        return "—"
    return f"{n(v['median'] * f, d)} [{n(v['p5'] * f, d)} ; {n(v['p95'] * f, d)}]"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arrondissement", type=int, required=True)
    ap.add_argument("--api", default="http://localhost")
    ap.add_argument("--replications", type=int, default=30)
    a = ap.parse_args()
    arr = a.arrondissement
    tok = os.environ.get("SALUBRI_ADMIN_TOKEN", "ouaga2026")
    with httpx.Client(base_url=a.api, timeout=60, headers={"X-Salubri-Token": tok}) as c:
        qs = c.get("/api/quartiers").json()
        qs = qs["features"] if isinstance(qs, dict) else qs
        mine = [q for q in qs if (q.get("properties") or q).get("arrondissement") == arr]
        if not mine:
            raise SystemExit(f"Aucun quartier de l'arrondissement {arr} dans quartiers.geojson")
        props = [q.get("properties") or q for q in mine]
        demo = any(p.get("source") == "demo" for p in props)
        base = next(s for s in c.get("/api/scenarios").json() if s["is_baseline"])
        bparams = c.get(f"/api/scenarios/{base['id']}").json()["params"]
        sid = scenario(c, f"Arrondissement {arr}", base["id"], {"active_quartier_ids": [p["id"] for p in props]})
        sc = c.get(f"/api/scenarios/{sid}").json()
        plan_id = sc["latest_ready_plan_id"]
        plan = c.get(f"/api/plans/{plan_id}").json()
        points = c.get(f"/api/plans/{plan_id}/points").json()["features"]
        routes = c.get(f"/api/plans/{plan_id}/routes").json()["features"]
        geo = c.get("/api/quartiers").json()
        geo = [q for q in (geo["features"] if isinstance(geo, dict) else geo) if q.get("geometry")]
        qgeo = [q for q in geo if (q.get("properties") or {}).get("arrondissement") == arr]
        variants: dict[str, dict[str, Any]] = {}
        variants["Référence"] = {"plan": plan, "sim": simulate(c, plan_id, a.replications)}
        # 2 camions en panne : les deux premiers camions du scénario
        vids = [v["id"] for v in sc["vehicles"] if not v.get("out_of_service")][:2]
        pid = c.patch(f"/api/scenarios/{sid}", json={"vehicles": [{"id": v, "out_of_service": True} for v in vids]})
        p2 = wait(c, pid.json()["plan_version_id"])
        variants["2 camions en panne"] = {"plan": p2, "sim": simulate(c, p2["id"], a.replications)}
        pid = c.patch(f"/api/scenarios/{sid}", json={"vehicles": [{"id": v, "out_of_service": False} for v in vids]})
        wait(c, pid.json()["plan_version_id"])
        p3 = wait(c, c.patch(f"/api/scenarios/{sid}", json={"params": {"season": "rain"}}).json()["plan_version_id"])
        variants["Saison des pluies"] = {"plan": p3, "sim": simulate(c, p3["id"], a.replications)}
        wait(c, c.patch(f"/api/scenarios/{sid}", json={"params": {"season": "dry"}}).json()["plan_version_id"])
        sub = round(min(0.8, bparams["subscription_rate"] * 1.2), 3)
        p4 = wait(
            c, c.patch(f"/api/scenarios/{sid}", json={"params": {"subscription_rate": sub}}).json()["plan_version_id"]
        )
        variants["Abonnements +20 %"] = {"plan": p4, "sim": simulate(c, p4["id"], a.replications)}
        wait(
            c,
            c.patch(
                f"/api/scenarios/{sid}", json={"params": {"subscription_rate": bparams["subscription_rate"]}}
            ).json()["plan_version_id"],
        )
        p5 = wait(c, c.patch(f"/api/scenarios/{sid}", json={"params": {
            "budget_fcfa_month": round(bparams["budget_fcfa_month"] * 0.7)}}).json()["plan_version_id"])  # fmt: skip
        variants["Budget −30 %"] = {"plan": p5, "sim": simulate(c, p5["id"], a.replications)}
        wait(c, c.patch(f"/api/scenarios/{sid}", json={"params": {
            "budget_fcfa_month": bparams["budget_fcfa_month"]}}).json()["plan_version_id"])  # fmt: skip
        # combinaison : saison des pluies et 2 camions en panne en même temps
        wait(c, c.patch(f"/api/scenarios/{sid}", json={"params": {"season": "rain"}}).json()["plan_version_id"])
        p6 = wait(c, c.patch(f"/api/scenarios/{sid}", json={
            "vehicles": [{"id": v, "out_of_service": True} for v in vids]}).json()["plan_version_id"])  # fmt: skip
        variants["Pluies + 2 camions en panne"] = {"plan": p6, "sim": simulate(c, p6["id"], a.replications)}
        wait(c, c.patch(f"/api/scenarios/{sid}", json={
            "vehicles": [{"id": v, "out_of_service": False} for v in vids]}).json()["plan_version_id"])  # fmt: skip
        wait(c, c.patch(f"/api/scenarios/{sid}", json={"params": {"season": "dry"}}).json()["plan_version_id"])
        rain_routes = c.get(f"/api/plans/{p3['id']}/routes").json()["features"]

    figs = ROOT / "docs/figures"
    figs.mkdir(parents=True, exist_ok=True)
    (figs / f"plan_arr{arr}_carte.svg").write_text(svg_map(points, routes, qgeo), encoding="utf-8")
    raw = {k: {"plan_id": v["plan"]["id"], "summary": v["plan"]["summary"], "sim": v["sim"]["metrics_summary"]}
           for k, v in variants.items()}  # fmt: skip
    (figs / f"plan_arr{arr}.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (ROOT / f"docs/PLAN_ARRONDISSEMENT_{arr}.md").write_text(
        render(arr, props, demo, plan, points, routes, variants, rain_routes, bparams, a.replications, qgeo),
        encoding="utf-8",
    )
    print(f"docs/PLAN_ARRONDISSEMENT_{arr}.md écrit ({len(points)} points, {len(routes)} tournées)")
    return 0


def quartier_of(lon: float, lat: float, qgeo: list[dict]) -> str:  # type: ignore[type-arg]
    from shapely.geometry import Point, shape

    pt = Point(lon, lat)
    best = min(qgeo, key=lambda q: shape(q["geometry"]).distance(pt), default=None)
    return (best or {}).get("properties", {}).get("name", "—") if best else "—"


def render(arr, props, demo, plan, points, routes, variants, rain_routes, bp, reps, qgeo) -> str:  # type: ignore[no-untyped-def]
    s = plan["summary"]
    ref = variants["Référence"]["sim"]["metrics_summary"]
    pop = sum(p["population"] for p in props)
    trucks = sorted({r["properties"]["vehicle_label"] for r in routes})
    pickups = bp["pickup_frequency_per_week"]
    days = {1: "lundi", 2: "lundi, jeudi", 3: "lundi, mercredi, vendredi"}.get(pickups, f"{pickups} jours par semaine")
    load_by_point: dict[str, tuple[str, float]] = {}
    for r in routes:
        pr = r["properties"]
        for st in pr["stops"]:
            load_by_point[st["point_key"]] = (f"{pr['vehicle_label']} r{pr['rotation']}", st["arrival_min"])
    L = [
        "<!-- SPDX-License-Identifier: CC-BY-4.0 -->",
        f"# Plan de collecte — Arrondissement {arr} de Ouagadougou",
        "",
        f"Généré par `scripts/plan_arrondissement.py --arrondissement {arr}` le {date.today().isoformat()}, plan "
        f"v{plan['version']} du scénario « Arrondissement {arr} » ; simulations du modèle à agents, {reps} "
        "réplications par variante, médiane [intervalle à 90 %]. Ne pas modifier à la main : relancer le script.",
        "",
    ]
    if demo:
        L += [
            "> **Données de démonstration.** Les limites et populations des quartiers de cet arrondissement viennent "
            "du jeu de démonstration (`quartiers.geojson`, `source: demo`) : "
            + ", ".join(f"{p['name']} ({n(p['population'], 0)} hab.)" for p in props)
            + ". Les bâtiments sont réels (Open Buildings) mais les populations sont des ordres de grandeur. Remplacer "
            "par les limites des secteurs et les populations du recensement (INSD) avant tout usage, puis relancer.",
            "",
        ]
    if arr in POP_INSD_2019:
        pop_demo = sum(p["population"] for p in props)
        L += [
            f"> **Population réelle** : {n(POP_INSD_2019[arr], 0)} habitants en 2019 (INSD, RGPH 2019, monographie de "
            "la commune de Ouagadougou, tableau 2.2), soit "
            f"{n(POP_INSD_2019[arr] / pop_demo, 1)} fois la population de démonstration ci-dessous. Les tonnages, "
            "le nombre de points et de camions sont donc à multiplier d'autant ; les limites des secteurs 37 à 40 ne "
            "sont pas publiées en données ouvertes (absentes de l'extrait OSM) : **à faire par l'équipe** "
            "(demander la carte des secteurs à la mairie d'arrondissement, la charger dans `quartiers.geojson`).",
            "",
        ]
    L += [
        "## En bref",
        "",
        f"- **Population couverte** : {n(pop, 0)} habitants ; **demande** {n(s['demand_t_week'])} t/semaine.",
        f"- **{len(points)} points de regroupement** (capacité {n(bp['collection_point_capacity_t'])} t), "
        f"couverture à {n(bp['walk_distance_max_m'], 0)} m de marche : "
        f"{n(100 * (s.get('coverage_walk') or 0), 0)} % de la population.",
        f"- **{len(trucks)} camion(s)** ({', '.join(trucks)}), {len(routes)} tournée(s) par jour d'enlèvement "
        f"({days}), {n(s['km_day'])} km, **{n(s['cost_day_fcfa'], 0)} FCFA** par jour d'enlèvement.",
        f"- Points non desservis : {s['unserved_points']} ; camions nécessaires pour tout desservir : "
        f"{s.get('trucks_needed', '—')} (disponibles : {s.get('vehicles_available', len(trucks))}).",
        "",
        f"![Carte des points et des tournées](figures/plan_arr{arr}_carte.svg)",
        "",
        "## Tournées (par jour d'enlèvement)",
        "",
        "| Camion | Rotation | Jours | 1er passage | Dernier passage | Points | Tonnage (t) | km | Coût (FCFA) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(routes, key=lambda r: (r["properties"]["vehicle_label"], r["properties"]["rotation"])):
        p = r["properties"]
        st = p["stops"]
        L.append(
            f"| {p['vehicle_label']} | {p['rotation']} | {days} | {hm(st[0]['arrival_min']) if st else '—'} "
            f"| {hm(st[-1]['arrival_min']) if st else '—'} | {len(st)} | {n(p['load_t'])} "
            f"| {n(p['distance_km'])} | {n(p['cost_fcfa'], 0)} |"
        )
    staff = len({(r["properties"]["vehicle_label"]) for r in routes})
    L += [
        "",
        "## Points de regroupement",
        "",
        "| Point | Position (lat, lon) | Quartier servi | Capacité (t) | Demande (t/sem.) "
        "| Remplissage par enlèvement | Îlots | Jours d'enlèvement | Créneau | Camion | Passage |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for f in sorted(points, key=lambda f: f["properties"]["key"]):
        p = f["properties"]
        tw = p.get("time_window") or [0, 0]
        cam, arr_min = load_by_point.get(p["key"], ("non desservi", None))
        lon, lat = f["geometry"]["coordinates"][:2]
        L.append(
            f"| {p['key']} | {lat:.5f}, {lon:.5f} | {quartier_of(lon, lat, qgeo)} | {n(bp['collection_point_capacity_t'])} "
            f"| {n(p['demand_t_week'], 2)} | {n(100 * p['fill_ratio_per_pickup'], 0)} % | {p['n_ilots']} "
            f"| {days if cam != 'non desservi' else '—'} | {hm(tw[0])}–{hm(tw[1])} | {cam} "
            f"| {hm(arr_min) if arr_min is not None else '—'} |"
        )
    L += [
        "",
        "## Coûts et personnel",
        "",
        f"- Coût par jour d'enlèvement : {n(s['cost_day_fcfa'], 0)} FCFA, soit ~{n(s['cost_day_fcfa'] * pickups * 52 / 12, 0)} "
        f"FCFA par mois ({pickups} enlèvements par semaine).",
        f"- Personnel par jour d'enlèvement : {staff} chauffeur(s) et {staff * STAFF_PER_TRUCK[1]} ripeur(s) "
        "(hypothèse : un chauffeur et deux ripeurs par camion).",
        "",
        "## Indicateurs simulés (90 jours)",
        "",
        "| Indicateur | " + " | ".join(variants) + " |",
        "|---|" + "---|" * len(variants),
    ]
    rows = [
        ("Tonnes collectées par camion", "collected_t", 1, 1.0),
        ("Tonnes pré-collectées", "precollected_t", 1, 1.0),
        ("Tonnes en dépôt sauvage", "wild_dump_t", 1, 1.0),
        ("Dépotoirs actifs (moyenne)", "wild_dumps_active_mean", 1, 1.0),
        ("Couverture simulée* (%)", "coverage_rate", 0, 100.0),
        ("Taux d'abonnement final (%)", "subscription_rate_final", 0, 100.0),
        ("Pré-collecteurs actifs (fin)", "precollectors_active_final", 0, 1.0),
        ("Coût de la mairie (FCFA/t)", "cost_per_t", 0, 1.0),
        ("Jours-points en débordement", "overflow_point_days", 0, 1.0),
    ]
    for lab, k, d, f in rows:
        L.append(f"| {lab} | " + " | ".join(iv(v["sim"]["metrics_summary"], k, d, f) for v in variants.values()) + " |")
    L += [
        "",
        "\\* Part de la population servie un jour donné : point à portée de marche **et pas plein**, ou passage du "
        "pré-collecteur dans les 7 jours. Plus stricte que la couverture du plan (distance seule).",
    ]
    p2 = variants["2 camions en panne"]["plan"]["summary"]
    coh = (p2.get("diff") or {}).get("coherence") or {}
    L += [
        "",
        "## Risques",
        "",
        f"- **Pannes** : avec 2 camions en moins, {p2['unserved_points']} points ne sont pas desservis "
        f"({s['unserved_points']} en référence) ; aucun point "
        f"ne bouge (points inchangés : {n(100 * (coh.get('points_inchanges_part') or 0), 0)} %), mais les tournées "
        f"sont refaites (camions sur les mêmes points : {n(100 * (coh.get('tournees_jaccard') or 0), 0)} %). "
        "Prévoir un camion de réserve ou une rotation supplémentaire.",
        f"- **Budget** : le plan coûte ~{n(s['cost_day_fcfa'] * pickups * 52 / 12, 0)} FCFA par mois en camions, sous le "
        f"budget même réduit de 30 % ({n(bp['budget_fcfa_month'] * 0.7, 0)} FCFA) : la variante « Budget −30 % » "
        "donne donc exactement la référence. Le budget ne limite les tournées que s'il descend sous ce coût "
        "(ou si la valeur de départ de la mairie est bien plus basse que celle de démonstration).",
        "- **Pré-collecte** : la charrette est le goulot (`SIMULATION_ODD.md` § 11) ; plus d'abonnés sans plus de "
        "pré-collecteurs n'augmente pas la pré-collecte.",
        "- **Données** : la quantité de déchets par habitant explique ~90 % de l'incertitude sur les dépôts "
        "(`SIMULATION_SENSIBILITE.md`) ; la mesurer par pesée dans l'arrondissement avant de dimensionner.",
        "",
        "## Saison des pluies",
        "",
    ]
    rs = variants["Saison des pluies"]["plan"]["summary"]
    L += [
        f"- Demande +15 % ({n(rs['demand_t_week'])} t/semaine) et vitesses réduites : {n(rs['km_day'])} km, "
        f"{n(rs['cost_day_fcfa'], 0)} FCFA par jour d'enlèvement, {rs['unserved_points']} point(s) non desservi(s), "
        f"{len(rain_routes)} tournée(s).",
        "- Avant les pluies : curer les caniveaux près des points, déplacer hors des zones inondables les bacs signalés "
        "« près de l'eau », vider les dépotoirs proches des cours d'eau en priorité (règle de nettoyage du plan).",
        "- Pendant : ajouter une rotation les jours après une forte pluie, garder un camion en réserve, renforcer les "
        "descentes Laabal dans les îlots récurrents en même temps que des rotations de camions (sinon les points "
        "débordent).",
        "",
        "## Indicateurs de suivi pour la mairie",
        "",
        "Chaque mois, comparer à la valeur simulée de référence (colonne « Référence ») ; un écart qui sort de "
        "l'intervalle à 90 % appelle une explication.",
        "",
        "| Indicateur | Comment le mesurer | Fréquence | Valeur simulée (référence) | Alerte si |",
        "|---|---|---|---|---|",
        f"| Tonnes collectées par camion | bons de pesée au CET | mensuelle | {iv(ref, 'collected_t')} t / 90 j "
        "| sous le 5ᵉ centile |",
        f"| Tonnes en dépôt sauvage | signalements vérifiés × volume (Salubri Map) | mensuelle "
        f"| {iv(ref, 'wild_dump_t')} t / 90 j | au-dessus du 95ᵉ centile |",
        "| Dépotoirs récurrents | Salubri Map, filtre « récurrent » | mensuelle "
        f"| {iv(ref, 'recurring_dumps')} | en hausse 2 mois de suite |",
        "| Points en débordement | photos des chefs de point / signalements « point plein » | hebdomadaire "
        f"| {iv(ref, 'overflow_point_days', 0)} jours-points / 90 j | un même point 2 semaines de suite |",
        "| Taux d'abonnement à la pré-collecte | registres des associations | trimestrielle "
        f"| {iv(ref, 'subscription_rate_final', 0, 100.0)} % | baisse de plus de 5 points |",
        f"| Coût par tonne | comptabilité (carburant, salaires, entretien) | mensuelle | {iv(ref, 'cost_per_t', 0)} FCFA/t "
        "| au-dessus du 95ᵉ centile |",
        "| Tournées faites / prévues | fiches de tournée signées | hebdomadaire | 100 % prévu | sous 90 % |",
        "",
    ]
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
