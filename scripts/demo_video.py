#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Prépare l'état de départ de la vidéo de 3 minutes (docs/VIDEO_SCRIPT.md) sur une pile lancée.

    python scripts/demo_video.py --api http://localhost [--arrondissement 9]

1. scénario « Vidéo — Arrondissement N » (quartiers de l'arrondissement), tous les camions en service, saison
   sèche, plan recalculé et prêt ;
2. photo de test (visage + plaque, domaine public / CC BY) copiée dans docs/video/photo_signalement.jpg pour la
   prise de vue « hors ligne + masquage » ;
3. affiche les identifiants utiles (scénario, plan, camions à mettre en panne) et la liste de contrôle.
Idempotent : relancer avant chaque prise efface le scénario vidéo précédent.
"""

import argparse
import os
import shutil
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost")
    ap.add_argument("--arrondissement", type=int, default=9)
    a = ap.parse_args()
    name = f"Vidéo — Arrondissement {a.arrondissement}"
    tok = os.environ.get("SALUBRI_ADMIN_TOKEN", "ouaga2026")
    with httpx.Client(base_url=a.api, timeout=60, headers={"X-Salubri-Token": tok}) as c:
        h = c.get("/api/health").json()
        if h.get("masking") != "ok":
            print("ATTENTION : masquage indisponible sur le serveur (modèles absents) — les photos seront refusées.")
        for s in c.get("/api/scenarios").json():
            if s["name"] == name:
                c.delete(f"/api/scenarios/{s['id']}")
        qs = c.get("/api/quartiers").json()["features"]
        ids = [q["properties"]["id"] for q in qs if q["properties"]["arrondissement"] == a.arrondissement]
        if not ids:
            print(f"Aucun quartier de l'arrondissement {a.arrondissement}", file=sys.stderr)
            return 2
        base = next(s for s in c.get("/api/scenarios").json() if s["is_baseline"])
        sid = c.post("/api/scenarios", json={"name": name, "parent_id": base["id"]}).json()["id"]
        sc = c.get(f"/api/scenarios/{sid}").json()
        pid = c.patch(
            f"/api/scenarios/{sid}",
            json={
                "params": {"active_quartier_ids": ids, "season": "dry"},
                "vehicles": [{"id": v["id"], "out_of_service": False} for v in sc["vehicles"]],
            },
        ).json()["plan_version_id"]
        for _ in range(300):
            p = c.get(f"/api/plans/{pid}").json()
            if p["status"] in ("ready", "failed"):
                break
            time.sleep(1)
        if p["status"] != "ready":
            print(f"Plan non prêt : {p['status']} {p.get('error')}", file=sys.stderr)
            return 1
        trucks = [v["label"] for v in sc["vehicles"]][:2]
    dest = ROOT / "docs/video/photo_signalement.jpg"
    shutil.copy(ROOT / "tests/e2e/fixtures/visage_et_plaque.jpg", dest)
    s = p["summary"]
    print(
        f"Scénario « {name} » prêt : {s['points']} points, {s['routes']} tournées, {s['unserved_points']} non desservis."
    )
    print(f"Camions à mettre en panne pendant la prise : {', '.join(trucks)}")
    print(f"Photo de la prise « hors ligne » : {dest}")
    print("Liste de contrôle : connecté en demo / ouaga2026 dans Salubri Map ; téléphone sur run/telephone ; "
          "Salubri Go déjà ouvert une fois (cache) ; enregistreur d'écran prêt.")  # fmt: skip
    return 0


if __name__ == "__main__":
    sys.exit(main())
