#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mesure du masquage des visages et des plaques sur un jeu annoté (docs/MASQUAGE.md).

    PYTHONPATH=apps/api python scripts/eval_masquage.py data/eval/masquage

Le dossier contient les photos et `annotations.json` :
    {"images": [{"fichier": "rue_001.jpg", "consentement": "oral, 2026-11-20",
                 "zones": [{"type": "visage", "x": 120, "y": 59, "w": 67, "h": 82},
                           {"type": "plaque", "x": 842, "y": 197, "w": 182, "h": 69}]}]}
Coordonnées en pixels de l'image telle qu'elle est enregistrée (déjà redressée).

Critères (les mêmes pour le jeu de terrain et le jeu public de contrôle) :
- **rappel** : une zone annotée compte comme masquée si au moins 70 % de sa surface est recouverte par les zones
  que l'application pixellise (cadres détectés + marge de 20 %), toutes catégories confondues ;
- **précision** : un cadre détecté est juste s'il recouvre une zone annotée de son type (IoU ≥ 0,3) ;
- zones ignorées : visages de moins de 20 px de haut, plaques de moins de 10 px de haut (illisibles de toute
  façon, comptées à part dans le rapport).
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from salubri_api.services.masking.detector import MARGIN, Box, detect

MIN_H = {"visage": 20, "plaque": 10}


def covered(gt: dict, preds: list[Box], width: int, height: int) -> float:
    x0, y0 = max(0, int(gt["x"])), max(0, int(gt["y"]))
    x1, y1 = min(width, int(np.ceil(gt["x"] + gt["w"]))), min(height, int(np.ceil(gt["y"] + gt["h"])))
    if x1 <= x0 or y1 <= y0:
        return 1.0
    m = np.zeros((y1 - y0, x1 - x0), bool)
    for b in preds:
        mx, my = b.w * MARGIN, b.h * MARGIN
        bx0, by0 = int(np.floor(b.x - mx)) - x0, int(np.floor(b.y - my)) - y0
        bx1, by1 = int(np.ceil(b.x + b.w + mx)) - x0, int(np.ceil(b.y + b.h + my)) - y0
        m[max(0, by0) : max(0, by1), max(0, bx0) : max(0, bx1)] = True
    return float(m.mean())


def iou(b: Box, g: dict) -> float:
    x1, y1 = max(b.x, g["x"]), max(b.y, g["y"])
    x2, y2 = min(b.x + b.w, g["x"] + g["w"]), min(b.y + b.h, g["y"] + g["h"])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = b.w * b.h + g["w"] * g["h"] - inter
    return inter / union if union > 0 else 0.0


def evaluate(folder: Path) -> dict:
    ann = json.loads((folder / "annotations.json").read_text(encoding="utf-8"))
    stats = {k: {"zones": 0, "masquees": 0, "ignorees": 0, "detections": 0, "justes": 0} for k in MIN_H}
    times, misses = [], []
    for item in ann["images"]:
        with Image.open(folder / item["fichier"]) as im:
            img = ImageOps.exif_transpose(im).convert("RGB")
        t0 = time.perf_counter()
        preds = detect(img)
        times.append(time.perf_counter() - t0)
        for g in item["zones"]:
            st = stats[g["type"]]
            if g["h"] < MIN_H[g["type"]]:
                st["ignorees"] += 1
                continue
            st["zones"] += 1
            if covered(g, preds, img.width, img.height) >= 0.7:
                st["masquees"] += 1
            else:
                misses.append({"fichier": item["fichier"], **g})
        for b in preds:
            st = stats[b.kind]
            st["detections"] += 1
            if any(g["type"] == b.kind and iou(b, g) >= 0.3 for g in item["zones"]):
                st["justes"] += 1
    out = {"images": len(ann["images"]), "temps_ms_median": round(statistics.median(times) * 1000, 1), "par_type": {}}
    for k, st in stats.items():
        out["par_type"][k] = {
            **st,
            "rappel": round(st["masquees"] / st["zones"], 3) if st["zones"] else None,
            "precision": round(st["justes"] / st["detections"], 3) if st["detections"] else None,
        }
    out["manques"] = misses[:50]
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("dossier", type=Path)
    p.add_argument("--json", type=Path, help="écrire le résultat complet dans ce fichier")
    a = p.parse_args(argv)
    r = evaluate(a.dossier)
    if a.json:
        a.json.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{r['images']} image(s), {r['temps_ms_median']} ms par photo (médiane, serveur)")
    for k, v in r["par_type"].items():
        print(
            f"  {k:7s} rappel {v['rappel']}  précision {v['precision']}  "
            f"({v['masquees']}/{v['zones']} zones masquées, {v['ignorees']} trop petites ignorées)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
