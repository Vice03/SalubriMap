#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Calage du facteur de détour du repli sans OSRM : km routiers OSRM / km à vol d'oiseau sur un échantillon de paires.

    PYTHONPATH=apps/api python scripts/calibrer_detour.py --osrm http://localhost:5000 --saison dry
    PYTHONPATH=apps/api python scripts/calibrer_detour.py --osrm http://localhost:5001 --saison rain

Échantillon : le dépôt et les points de regroupement du dernier plan prêt du scénario de base, `--paires` paires
tirées au hasard (graine fixe), distances OSRM par /table. Résultat : facteur médian, quartiles, et erreur du repli
sur chaque paire avec le facteur actuel et avec le facteur calé (erreur absolue moyenne en %, et en km sur une
tournée type). Écrit docs/DETOUR_CALIBRATION.md (une section par saison) et docs/detour_calibration.json. La valeur
calée se recopie à la main dans params_default.json (fallback_detour_dry / fallback_detour_rain).

Il faut OSRM : sur la machine de démonstration, `docker compose --profile osrm up -d` puis lancer ce script dans le
conteneur API (`docker compose exec api python /app/scripts/calibrer_detour.py --osrm http://osrm:5000 …`).
"""

import argparse
import json
import random
import sys
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def fit(crow_km: np.ndarray, road_km: np.ndarray, current: float) -> dict[str, float]:
    """Facteur médian du rapport route / vol d'oiseau, et erreur du repli avec l'actuel et le calé.

    On garde la médiane (et non la moyenne) : quelques paires très courtes ont des rapports extrêmes (sens unique,
    pont) qui ne doivent pas tirer le facteur. Les paires de moins de 200 m sont exclues pour la même raison."""
    keep = crow_km >= 0.2
    c, r = crow_km[keep], road_km[keep]
    ratio = r / c
    med = float(np.median(ratio))

    def mape(f: float) -> float:
        return float(np.mean(np.abs(c * f - r) / r))

    return {
        "paires": int(keep.sum()),
        "facteur_median": round(med, 3),
        "q1": round(float(np.percentile(ratio, 25)), 3),
        "q3": round(float(np.percentile(ratio, 75)), 3),
        "facteur_actuel": current,
        "erreur_moyenne_actuel": round(mape(current), 4),
        "erreur_moyenne_cale": round(mape(med), 4),
        "biais_actuel": round(float(np.sum(c * current) / np.sum(r) - 1), 4),
    }


def sample_nodes() -> list[tuple[float, float]]:
    from shapely import wkb

    from salubri_api.db import get_sessionmaker
    from salubri_api.models import CollectionPoint, Commune, PlanVersion, Scenario

    with get_sessionmaker()() as s:
        sc = s.query(Scenario).filter(Scenario.parent_id.is_(None)).order_by(Scenario.created_at).first()
        if sc is None:
            raise SystemExit("Aucun scénario : lancer la démo (seed)")
        pv = (
            s.query(PlanVersion)
            .filter(PlanVersion.scenario_id == sc.id, PlanVersion.status == "ready")
            .order_by(PlanVersion.version.desc())
            .first()
        )
        depot = wkb.loads(bytes(s.get(Commune, sc.commune_id).depot_geom.data))
        pts = s.query(CollectionPoint).filter(CollectionPoint.plan_version_id == pv.id).all()
        return [(depot.x, depot.y)] + [(g.x, g.y) for g in (wkb.loads(bytes(p.geom.data)) for p in pts)]


def main() -> int:
    from salubri_api.services.geo import haversine_matrix_m
    from salubri_api.services.params import ScenarioParams
    from salubri_api.services.planning.distance import _osrm_table

    ap = argparse.ArgumentParser()
    ap.add_argument("--osrm", required=True, help="URL du serveur OSRM (graphe de la saison)")
    ap.add_argument("--saison", choices=["dry", "rain"], default="dry")
    ap.add_argument("--paires", type=int, default=400)
    a = ap.parse_args()
    nodes = sample_nodes()
    rng = random.Random(2026)
    idx = sorted(rng.sample(range(len(nodes)), min(len(nodes), 60)))  # 60 nœuds → jusqu'à 3540 paires
    sub = [nodes[i] for i in idx]
    try:
        road, _ = _osrm_table(sub, a.osrm.rstrip("/"), timeout=30)
    except Exception as exc:  # noqa: BLE001
        print(f"OSRM injoignable à {a.osrm} ({exc}) : rien n'est écrit.", file=sys.stderr)
        return 2
    arr = np.array(sub)
    crow = haversine_matrix_m(arr[:, 1], arr[:, 0]) / 1000
    pairs = [(i, j) for i in range(len(sub)) for j in range(len(sub)) if i != j]
    pairs = rng.sample(pairs, min(a.paires, len(pairs)))
    c = np.array([crow[i, j] for i, j in pairs])
    r = np.array([road[i, j] for i, j in pairs])
    d = ScenarioParams()
    current = d.fallback_detour_rain if a.saison == "rain" else d.fallback_detour_dry
    res = {"date": date.today().isoformat(), "osrm": a.osrm, **fit(c, r, current)}
    jf = ROOT / "docs/detour_calibration.json"
    allres = json.loads(jf.read_text(encoding="utf-8")) if jf.exists() else {}
    allres[a.saison] = res
    jf.write_text(json.dumps(allres, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    nom = {"dry": "Saison sèche (graphe `car`)", "rain": "Saison des pluies (graphe `car_rain`)"}
    md = [
        "<!-- SPDX-License-Identifier: CC-BY-4.0 -->",
        "# Calage du facteur de détour (repli sans OSRM)",
        "",
        "Généré par `scripts/calibrer_detour.py` à partir de distances OSRM réelles. Sans OSRM, les tournées utilisent "
        "« km à vol d'oiseau × facteur » ; ce facteur (`fallback_detour_dry`, `fallback_detour_rain`) est un paramètre "
        "du scénario. On le cale sur la médiane du rapport km OSRM / km à vol d'oiseau (paires de plus de 200 m).",
        "",
    ]
    for k in ("dry", "rain"):
        if k not in allres:
            md += [f"## {nom[k]}", "", "Pas encore mesuré : lancer le script avec `--saison " + k + "`.", ""]
            continue
        v = allres[k]
        md += [
            f"## {nom[k]}",
            "",
            f"Mesuré le {v['date']} sur {v['paires']} paires (OSRM {v['osrm']}).",
            "",
            "| Facteur médian | Quartiles | Facteur actuel | Erreur moyenne par paire, actuel → calé "
            "| Biais total des km, actuel |",
            "|---|---|---|---|---|",
            f"| {v['facteur_median']} | {v['q1']} – {v['q3']} | {v['facteur_actuel']} "
            f"| {100 * v['erreur_moyenne_actuel']:.1f} % → {100 * v['erreur_moyenne_cale']:.1f} % "
            f"| {100 * v['biais_actuel']:+.1f} % |",
            "",
        ]
    (ROOT / "docs/DETOUR_CALIBRATION.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
