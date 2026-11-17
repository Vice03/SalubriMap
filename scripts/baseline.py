#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Référence « modules éteints » : photographie des plans des scénarios et comparaison entre deux photographies.

    PYTHONPATH=apps/api python scripts/baseline.py photo data/baseline/plans.json
    PYTHONPATH=apps/api python scripts/baseline.py compare data/baseline/plans.json /tmp/plans.json
    PYTHONPATH=apps/api python scripts/baseline.py recalcul /tmp/plans.json   # recalcule puis photographie

Pour comparer deux versions du code, partir de la même base (mêmes identifiants d'îlots : une copie de la base de
référence, `CREATE DATABASE x TEMPLATE salubri_base`), avec `SALUBRI_DETERMINISTIC_SOLVERS=true` : `recalcul`
relance un calcul complet de chaque scénario (comme « Recalcul complet manuel ») puis photographie.

Pour chaque scénario, dernier plan prêt : résumé (sans durées ni horodatages), points (clé, position au mètre,
demande, capacité), tournées (camion, rotation, arrêts, km, charge). Sert à prouver qu'un module optionnel
éteint ne change rien (règle 1 du prompt des modules). La comparaison ignore ce qui dépend de l'heure et de la
vitesse de la machine ; tout le reste doit être identique.
"""

import json
import sys
from pathlib import Path
from typing import Any

# champs qui dépendent de la machine ou de l'heure, pas du plan
VOLATILE = {"duration_ms", "duree_ms", "duration_s", "created_at", "finished_at", "started_at", "plan_id",
            "previous_plan_id", "id", "stages_ms", "cache"}  # fmt: skip


def _clean(v: Any) -> Any:
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in sorted(v.items()) if k not in VOLATILE and not k.endswith("_ms")}
    if isinstance(v, list):
        return [_clean(x) for x in v]
    if isinstance(v, float):
        return round(v, 6)
    return v


def photo() -> dict[str, Any]:
    from shapely import wkb

    from salubri_api.db import get_sessionmaker
    from salubri_api.models import CollectionPoint, PlanVersion, Route, RouteStop, Scenario, Vehicle

    out: dict[str, Any] = {}
    with get_sessionmaker()() as s:
        for sc in s.query(Scenario).order_by(Scenario.name).all():
            pv = (
                s.query(PlanVersion)
                .filter(PlanVersion.scenario_id == sc.id, PlanVersion.status == "ready")
                .order_by(PlanVersion.version.desc())
                .first()
            )
            if pv is None:
                continue
            cps = (
                s.query(CollectionPoint).filter(CollectionPoint.plan_version_id == pv.id).order_by(CollectionPoint.idx)
            )
            keys = {}
            points = []
            for p in cps:
                g = wkb.loads(bytes(p.geom.data))
                keys[p.id] = p.key
                points.append([p.key, round(g.x, 5), round(g.y, 5), round(p.demand_t_week, 4), p.capacity_t, p.frozen])
            labels = {v.id: v.label for v in s.query(Vehicle).filter(Vehicle.scenario_id == sc.id)}
            routes = []
            for r in s.query(Route).filter(Route.plan_version_id == pv.id).all():
                stops = s.query(RouteStop).filter(RouteStop.route_id == r.id).order_by(RouteStop.seq)
                routes.append([labels.get(r.vehicle_id), r.rotation, [keys.get(st.collection_point_id) for st in stops],
                               round(r.distance_km, 3), round(r.load_t, 3)])  # fmt: skip
            out[sc.name] = {
                "version": pv.version,
                "summary": _clean(pv.summary or {}),
                "points": points,
                "routes": sorted(routes, key=lambda x: (str(x[0]), x[1])),
            }
    return out


def diff(a: Any, b: Any, path: str = "") -> list[str]:
    if type(a) is not type(b):
        return [f"{path}: {a!r} → {b!r}"]
    if isinstance(a, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{path}/{k}: {'absent' if k not in a else a[k]!r} → {'absent' if k not in b else b[k]!r}")
            else:
                out += diff(a[k], b[k], f"{path}/{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path}: {len(a)} éléments → {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b, strict=True)) for d in diff(x, y, f"{path}[{i}]")]
    return [] if a == b else [f"{path}: {a!r} → {b!r}"]


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "photo":
        Path(sys.argv[2]).parent.mkdir(parents=True, exist_ok=True)
        Path(sys.argv[2]).write_text(json.dumps(photo(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{sys.argv[2]} écrit")
        return 0
    if len(sys.argv) >= 3 and sys.argv[1] == "recalcul":
        from salubri_api.db import get_sessionmaker
        from salubri_api.models import Scenario
        from salubri_api.services.plan.pipeline import request_recompute

        with get_sessionmaker()() as s:
            for sc in s.query(Scenario).order_by(Scenario.name).all():
                pv = request_recompute(s, sc, "manual", {"reason": "contrôle modules éteints"}, sync=True)
                print(f"{sc.name} : v{pv.version} {pv.status}")
        Path(sys.argv[2]).write_text(json.dumps(photo(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{sys.argv[2]} écrit")
        return 0
    if len(sys.argv) == 4 and sys.argv[1] == "compare":
        a, b = (json.loads(Path(p).read_text(encoding="utf-8")) for p in sys.argv[2:4])
        d = diff(a, b)
        for line in d[:60]:
            print(line)
        print(f"{len(d)} différence(s)" if d else "identique")
        return 1 if d else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
