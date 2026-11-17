# SPDX-License-Identifier: AGPL-3.0-or-later
"""Replay the jury's live test against a running Salubri API and write docs/REHEARSAL_REPORT.md.

1. imports the trap set generated for the loaded map, data/rehearsal/traps/<carte>/traps.geojson (+ photos), and
   checks every trap against traps_expected.json (<carte> comes from GET /api/communes/{slug});
2. on a scratch clone of the baseline scenario, applies data/rehearsal/scenario_changes.yaml step by step,
   follows the SSE progress, times each recompute and checks the invariants.
Exit code 0 only if everything passes.

    python scripts/rehearse.py [--api http://localhost] [--traps-only] [--keep]
"""

import argparse
import io
import json
import os
import sys
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

from _common import DATA, ROOT
from salubri_api.seed.synthetic import photo_for_name

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"


def ok(flag: bool) -> str:
    return f"{GREEN}OK{RESET}" if flag else f"{RED}ÉCHEC{RESET}"


def traps_dir(c: httpx.Client) -> tuple[Path, str]:
    """Folder of the trap set generated for the base map the API has loaded (see services/dataset.py)."""
    slug = os.environ.get("SALUBRI_COMMUNE", "ouagadougou")
    key = c.get(f"/api/communes/{slug}").json().get("dataset", "")
    folder = DATA / "rehearsal" / "traps" / key
    if key and (folder / "traps.geojson").exists():
        return folder, key
    legacy = DATA / "rehearsal"
    if (legacy / "traps.geojson").exists():  # ancien emplacement unique, avant les jeux par carte
        print(
            f"{RED}Attention{RESET} : pas de jeu pour la carte « {key} », ancien jeu data/rehearsal/traps.geojson utilisé."
        )
        return legacy, f"{key} (ancien jeu, à régénérer : make gen-traps)"
    sys.exit(
        f"Aucun jeu de pièges pour la carte chargée « {key or 'inconnue'} ». "
        "Générez-le d'abord : make gen-traps (ou python scripts/gen_traps.py)."
    )


def traps_zip(folder: Path) -> bytes:
    fc = json.loads((folder / "traps.geojson").read_text(encoding="utf-8"))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("traps.geojson", json.dumps(fc))
        for name in {f["properties"].get("photo") for f in fc["features"] if f["properties"].get("photo")}:
            data = photo_for_name(name)
            if data:
                z.writestr(f"photos/{name}", data)
    return buf.getvalue()


def run_traps(c: httpx.Client) -> tuple[bool, list[str]]:
    folder, key = traps_dir(c)
    print(f"Pièges : jeu « {key} »")
    for b in c.get("/api/imports").json():
        if b["filename"] == "traps.zip" and not b["rolled_back"]:
            c.post(f"/api/imports/{b['id']}/rollback")
    before = len(c.get("/api/dump-sites").json()["features"])
    expected = json.loads((folder / "traps_expected.json").read_text(encoding="utf-8"))
    r = c.post("/api/imports", files={"file": ("traps.zip", traps_zip(folder), "application/zip")}, timeout=120)
    r.raise_for_status()
    rows = {row["external_id"]: row for row in r.json()["report"] if row.get("external_id")}
    lines = [
        f"Jeu de pièges : `{key}`",
        "",
        "| Piège | Attendu | Obtenu | Règles | Résultat |",
        "|---|---|---|---|---|",
    ]
    all_ok = True
    print(f"\n{'Piège':28} {'attendu':22} {'obtenu':12} {'score':>5}  règles")
    for eid, exp in expected.items():
        row = rows.get(eid)
        got = row["report_status"] if row else "absent"
        rules = sorted({h["rule"] for h in (row or {}).get("rule_hits", [])})
        good = row is not None and got in exp["status"] and set(exp["rules"]) <= set(rules)
        all_ok &= good
        print(
            f"{eid:28} {'/'.join(exp['status']):22} {got:12} {str((row or {}).get('score')):>5}  "
            f"{','.join(rules) or '—':14} {ok(good)}"
        )
        lines.append(
            f"| {eid} | {'/'.join(exp['status'])} {' '.join(exp['rules'])} | {got} ({(row or {}).get('score')}) "
            f"| {', '.join(rules) or '—'} | {'✅' if good else '❌'} |"
        )
    after = len(c.get("/api/dump-sites").json()["features"])
    stable = after == before
    all_ok &= stable
    print(f"\nDépotoirs consolidés avant/après les pièges : {before} → {after}  {ok(stable)}")
    lines.append(f"\nDépotoirs consolidés avant/après : {before} → {after} {'✅' if stable else '❌'}")
    return all_ok, lines


def wait_plan(c: httpx.Client, plan_id: str, timeout_s: float = 60) -> tuple[dict[str, Any], float]:
    t0 = time.perf_counter()
    with c.stream("GET", f"/api/plans/{plan_id}/events", timeout=timeout_s) as resp:
        for line in resp.iter_lines():
            if line.startswith("event:") and line.split(":", 1)[1].strip() in ("ready", "failed", "superseded"):
                break
    plan = c.get(f"/api/plans/{plan_id}").json()
    if plan["status"] == "superseded":  # merged into a later version: follow it
        latest = c.get(f"/api/scenarios/{plan['scenario_id']}").json()["latest_plan_id"]
        if latest and latest != plan_id:
            return wait_plan(c, latest, timeout_s)
    return plan, time.perf_counter() - t0


def invariants(
    c: httpx.Client,
    plan: dict[str, Any],
    prev_points: dict[str, list[float]] | None,
    step: dict[str, Any],
    polygon: list[list[float]] | None,
) -> list[str]:
    errors = []
    if plan["status"] != "ready":
        return [f"plan {plan['status']} : {plan.get('error')}"]
    if plan["summary"].get("points_constraint_relaxed"):
        errors.append(f"{plan['summary']['points_constraint_relaxed']} point(s) hors contraintes")
    for f in c.get(f"/api/plans/{plan['id']}/routes").json()["features"]:
        p = f["properties"]
        if p["load_t"] > p["capacity_t"] + 1e-6:
            errors.append(f"tournée {p['vehicle_label']} surchargée")
    if step.get("check_frozen") and prev_points:
        pts = {
            f["properties"]["key"]: f["geometry"]["coordinates"]
            for f in c.get(f"/api/plans/{plan['id']}/points").json()["features"]
        }
        moved = [
            k for k, xy in prev_points.items() if k not in pts or abs(pts[k][0] - xy[0]) + abs(pts[k][1] - xy[1]) > 1e-6
        ]
        if moved:
            errors.append(f"{len(moved)} point(s) existant(s) déplacé(s)")
        if polygon:
            from shapely.geometry import Point, Polygon

            poly = Polygon(polygon)
            if not any(poly.buffer(0.003).contains(Point(*xy)) for k, xy in pts.items() if k not in prev_points):
                errors.append("aucun nouveau point pour le nouveau quartier")
    return errors


def wait_idle(c: httpx.Client, timeout: float = 300) -> None:
    """Attend que la file de recalculs du serveur soit vide (/api/health → queue), au plus `timeout` s."""
    time.sleep(0.5)
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        q = c.get("/api/health").json().get("queue")
        if q is None:  # serveur antérieur à 0.3 : ancienne attente fixe
            time.sleep(3)
            return
        if not any(q.values()):
            return
        time.sleep(0.5)
    print("Attention : la file de recalculs n'est pas vide après", timeout, "s")


def run_changes(c: httpx.Client, keep: bool) -> tuple[bool, list[str]]:
    spec = yaml.safe_load((DATA / "rehearsal" / "scenario_changes.yaml").read_text(encoding="utf-8"))
    wait_idle(
        c
    )  # le recalcul différé déclenché par l'import doit être fini (sinon « 2 camions en panne » recalcule E1–E4)
    base = next(s for s in c.get("/api/scenarios").json() if s["is_baseline"])
    clone = c.post(
        "/api/scenarios", json={"name": f"Répétition {datetime.now(UTC):%H:%M:%S}", "parent_id": base["id"]}
    ).json()
    sid = clone["id"]
    wait_plan(c, clone["plan_version_id"])
    vehicles = {v["label"]: v["id"] for v in c.get(f"/api/scenarios/{sid}").json()["vehicles"]}
    original_budget = clone["params"]["budget_fcfa_month"]
    lines = [
        "| Étape | Événement | Étapes recalculées | En cache | Durée serveur | Durée totale | Invariants |",
        "|---|---|---|---|---|---|---|",
    ]
    all_ok = True
    created_quartier = None
    print(f"\n{'Étape':34} {'recalculé':22} {'cache':16} {'serveur':>8} {'total':>7}  invariants")
    for step in spec["steps"]:
        prev = c.get(f"/api/scenarios/{sid}").json()["latest_ready_plan_id"]
        prev_pts = (
            {
                f["properties"]["key"]: f["geometry"]["coordinates"]
                for f in c.get(f"/api/plans/{prev}/points").json()["features"]
            }
            if prev
            else None
        )
        polygon = None
        t0 = time.perf_counter()
        act = step["action"]
        if act == "breakdown":
            flag = step.get("out_of_service", True)
            if len(step["vehicles"]) == 1:
                plan_id = c.post(
                    f"/api/scenarios/{sid}/vehicles/{vehicles[step['vehicles'][0]]}/breakdown",
                    json={"out_of_service": flag},
                ).json()["plan_version_id"]
            else:  # several trucks at once: one PATCH, one event
                plan_id = c.patch(
                    f"/api/scenarios/{sid}",
                    json={"vehicles": [{"id": vehicles[v], "out_of_service": flag} for v in step["vehicles"]]},
                ).json()["plan_version_id"]
        elif act == "params":
            params = dict(step["params"])
            if "budget_factor" in params:
                params["budget_fcfa_month"] = original_budget * params.pop("budget_factor")
            plan_id = c.patch(f"/api/scenarios/{sid}", json={"params": params}).json()["plan_version_id"]
        elif act == "new_quartier":
            polygon = step["polygon"]
            body = c.post(
                "/api/quartiers",
                json={
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [polygon]},
                    "properties": {"name": step["name"], "population": step["population"], "scenario_id": sid},
                },
            ).json()
            created_quartier = body["quartier"]["properties"]["id"]
            plan_id = body["plans"][0]["plan_version_id"]
        elif act == "double_patch":
            c.patch(f"/api/scenarios/{sid}", json={"params": {"seed": 7}})
            time.sleep(0.1)
            plan_id = c.patch(f"/api/scenarios/{sid}", json={"params": {"seed": 42}}).json()["plan_version_id"]
        else:
            raise SystemExit(f"action inconnue : {act}")
        plan, _ = wait_plan(c, plan_id)
        total = time.perf_counter() - t0
        stages = plan.get("stages") or []
        ran = [s["stage"] for s in stages if not s["cache_hit"]]
        hit = [s["stage"] for s in stages if s["cache_hit"]]
        errs = invariants(c, plan, prev_pts, step, polygon)
        if not set(step.get("must_run", [])) <= set(ran):
            errs.append(f"aurait dû recalculer {sorted(set(step['must_run']) - set(ran))}")
        if not set(step.get("must_hit", [])) <= set(hit):
            errs.append(f"aurait dû réutiliser {sorted(set(step['must_hit']) - set(hit))}")
        server = (plan.get("summary") or {}).get("duration_ms", 0) / 1000
        if server > step.get("max_s", 5):
            errs.append(f"{server:.1f} s > {step.get('max_s', 5)} s")
        if act == "double_patch":
            versions = c.get(f"/api/scenarios/{sid}").json()
            if versions["latest_plan_status"] not in ("ready",):
                errs.append("dernière version non prête")
        good = not errs
        all_ok &= good
        print(
            f"{step['name']:34} {','.join(ran):22} {','.join(hit) or '—':16} {server:7.2f}s {total:6.2f}s  "
            f"{ok(good)} {DIM}{'; '.join(errs)}{RESET}"
        )
        lines.append(
            f"| {step['name']} | {plan.get('event')} | {', '.join(ran)} | {', '.join(hit) or '—'} | {server:.2f} s "
            f"| {total:.2f} s | {'✅' if good else '❌ ' + '; '.join(errs)} |"
        )
    if not keep:
        if created_quartier:
            c.delete(f"/api/quartiers/{created_quartier}")
        c.delete(f"/api/scenarios/{sid}")
    return all_ok, lines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost")
    ap.add_argument("--traps-only", action="store_true")
    ap.add_argument("--keep", action="store_true", help="garder le scénario de répétition")
    a = ap.parse_args()
    token = os.environ.get("SALUBRI_ADMIN_TOKEN", "ouaga2026")
    with httpx.Client(base_url=a.api, timeout=30, headers={"X-Salubri-Token": token}) as c:
        h = c.get("/api/health").json()
        print(f"API {a.api} : base {h['db']}, OSRM {h['osrm']}")
        traps_ok, traps_lines = run_traps(c)
        changes_ok, change_lines = (True, []) if a.traps_only else run_changes(c, a.keep)
    report = [
        "# Rapport de répétition de l'épreuve",
        "",
        f"Généré le {datetime.now(UTC):%d/%m/%Y %H:%M} UTC — API {a.api}, OSRM {h['osrm']}.",
        "",
        "## Signalements piégés",
        "",
        *traps_lines,
    ]
    if not a.traps_only:
        report += ["", "## Changements de paramètres", "", *change_lines]
    report += ["", f"**Résultat : {'tout est vert' if traps_ok and changes_ok else 'des contrôles échouent'}.**", ""]
    out = ROOT / "docs" / "REHEARSAL_REPORT.md"
    out.write_text("\n".join(report), encoding="utf-8")
    print(f"\nRapport écrit dans {out.relative_to(ROOT)}")
    sys.exit(0 if traps_ok and changes_ok else 1)


if __name__ == "__main__":
    main()
