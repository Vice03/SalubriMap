#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mesure du masquage des visages et des plaques sur un jeu annoté (docs/MASQUAGE.md).

    PYTHONPATH=apps/api python scripts/eval_masquage.py data/eval/masquage --rapport docs/MASQUAGE_EVALUATION.md \
        --nom "Jeu de terrain, Ouagadougou"

Le dossier contient les photos et `annotations.json` :
    {"images": [{"fichier": "rue_001.jpg", "consentement": "oral, 2026-11-20",
                 "zones": [{"type": "visage", "x": 120, "y": 59, "w": 67, "h": 82},
                           {"type": "plaque", "sous_type": "moto", "x": 842, "y": 197, "w": 182, "h": 69}]}]}
Coordonnées en pixels de l'image telle qu'elle est enregistrée (déjà redressée). `sous_type` (plaques) : « moto »
ou « voiture », facultatif. Classe de taille calculée d'après la hauteur : petite < 40 px, moyenne 40–100 px,
grande ≥ 100 px. Préparer le fichier : scripts/annoter_masquage.py.

Deux chaînes mesurées :
- **téléphone** : la détection de Salubri Go (même code que le serveur, `detector.detect`) sur la photo d'origine ;
- **téléphone + serveur** : en plus, la seconde passe du serveur sur la photo déjà masquée par le téléphone (ce qui
  est réellement enregistré).

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

from salubri_api.services.masking.detector import MARGIN, Box, detect, pixelate

MIN_H = {"visage": 20, "plaque": 10}
BUCKETS = (("petite", 0, 40), ("moyenne", 40, 100), ("grande", 100, 1e9))
TARGET = {"visage": 0.95, "plaque": 0.90}


def bucket(h: float) -> str:
    return next(n for n, lo, hi in BUCKETS if lo <= h < hi)


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


def _empty() -> dict:
    return {"zones": 0, "masquees": 0}


def evaluate(folder: Path) -> dict:
    ann = json.loads((folder / "annotations.json").read_text(encoding="utf-8"))
    chains = ("telephone", "telephone_serveur")
    stats = {
        c: {k: {"zones": 0, "masquees": 0, "ignorees": 0, "detections": 0, "justes": 0} for k in MIN_H} for c in chains
    }
    by_size = {c: {k: {n: _empty() for n, _, _ in BUCKETS} for k in MIN_H} for c in chains}
    by_sub: dict[str, dict[str, dict]] = {c: {} for c in chains}
    times, misses = [], []
    for item in ann["images"]:
        with Image.open(folder / item["fichier"]) as im:
            img = ImageOps.exif_transpose(im).convert("RGB")
        t0 = time.perf_counter()
        phone = detect(img)
        times.append(time.perf_counter() - t0)
        arr = np.array(img)
        pixelate(arr, phone)
        second = detect(Image.fromarray(arr))  # ce que le serveur trouve encore sur la photo masquée
        for chain, preds in (("telephone", phone), ("telephone_serveur", phone + second)):
            st_all = stats[chain]
            for g in item["zones"]:
                st = st_all[g["type"]]
                if g["h"] < MIN_H[g["type"]]:
                    st["ignorees"] += 1
                    continue
                ok = covered(g, preds, img.width, img.height) >= 0.7
                st["zones"] += 1
                st["masquees"] += ok
                bs = by_size[chain][g["type"]][bucket(g["h"])]
                bs["zones"] += 1
                bs["masquees"] += ok
                if g.get("sous_type"):
                    sub = by_sub[chain].setdefault(f"{g['type']} {g['sous_type']}", _empty())
                    sub["zones"] += 1
                    sub["masquees"] += ok
                if not ok and chain == "telephone_serveur":
                    misses.append({"fichier": item["fichier"], **g})
            for b in preds:
                st = st_all[b.kind]
                st["detections"] += 1
                if any(g["type"] == b.kind and iou(b, g) >= 0.3 for g in item["zones"]):
                    st["justes"] += 1

    def rate(a: int, n: int) -> float | None:
        return round(a / n, 3) if n else None

    out: dict = {"images": len(ann["images"]), "temps_ms_median": round(statistics.median(times) * 1000, 1)}
    for chain in chains:
        out[chain] = {
            k: {
                **st,
                "rappel": rate(st["masquees"], st["zones"]),
                "precision": rate(st["justes"], st["detections"]),
                "par_taille": {
                    n: {**v, "rappel": rate(v["masquees"], v["zones"])} for n, v in by_size[chain][k].items()
                },
            }
            for k, st in stats[chain].items()
        }
        out[chain]["sous_types"] = {
            n: {**v, "rappel": rate(v["masquees"], v["zones"])} for n, v in by_sub[chain].items()
        }
    out["par_type"] = out["telephone_serveur"]  # compatibilité (figures du rapport)
    out["manques"] = misses[:50]
    return out


def report(r: dict, name: str) -> str:
    """docs/MASQUAGE_EVALUATION.md : tableaux par chaîne, type et taille, et comparaison aux cibles."""

    def f(x: float | None) -> str:
        return "—" if x is None else f"{x:.3f}".replace(".", ",")

    L = [
        "<!-- SPDX-License-Identifier: CC-BY-4.0 -->",
        "# Évaluation du masquage",
        "",
        f"Généré par `scripts/eval_masquage.py` — **{name}**, {r['images']} images, {r['temps_ms_median']} ms par "
        "photo (médiane, serveur, chaîne téléphone). Critères : `scripts/eval_masquage.py` (zone masquée si ≥ 70 % "
        "de sa surface est pixellisée ; détection juste si IoU ≥ 0,3 ; visages < 20 px et plaques < 10 px de haut "
        "ignorés). Cibles : rappel ≥ 0,95 visages, ≥ 0,90 plaques.",
        "",
    ]
    for chain, title in (
        ("telephone", "Téléphone seul"),
        ("telephone_serveur", "Téléphone + seconde passe du serveur"),
    ):
        L += [
            f"## {title}",
            "",
            "| Type | Rappel | Précision | Cible | Atteinte | Zones | Ignorées |",
            "|---|---|---|---|---|---|---|",
        ]
        for k, v in ((k, r[chain][k]) for k in MIN_H):
            ok = "oui" if v["rappel"] is not None and v["rappel"] >= TARGET[k] else "**non**"
            L.append(
                f"| {k} | {f(v['rappel'])} | {f(v['precision'])} | {f(TARGET[k])} | {ok} | {v['zones']} | {v['ignorees']} |"
            )
        L += ["", "| Type | Petites (< 40 px) | Moyennes (40–100 px) | Grandes (≥ 100 px) |", "|---|---|---|---|"]
        for k in MIN_H:
            cells = [f"{f(v['rappel'])} ({v['masquees']}/{v['zones']})" for v in r[chain][k]["par_taille"].values()]
            L.append(f"| {k} | " + " | ".join(cells) + " |")
        subs = r[chain].get("sous_types") or {}
        if subs:
            L += ["", "| Sous-type | Rappel | Zones |", "|---|---|---|"]
            L += [f"| {n} | {f(v['rappel'])} | {v['zones']} |" for n, v in sorted(subs.items())]
        L.append("")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("dossier", type=Path)
    p.add_argument("--json", type=Path, help="écrire le résultat complet dans ce fichier")
    p.add_argument("--rapport", type=Path, help="écrire le rapport Markdown (docs/MASQUAGE_EVALUATION.md)")
    p.add_argument("--nom", default="jeu sans nom", help="nom du jeu, écrit dans le rapport")
    a = p.parse_args(argv)
    r = evaluate(a.dossier)
    if a.json:
        a.json.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    if a.rapport:
        a.rapport.write_text(report(r, a.nom), encoding="utf-8")
    print(f"{r['images']} image(s), {r['temps_ms_median']} ms par photo (médiane, serveur)")
    for chain in ("telephone", "telephone_serveur"):
        for k in MIN_H:
            v = r[chain][k]
            print(
                f"  {chain:17s} {k:7s} rappel {v['rappel']}  précision {v['precision']}  "
                f"({v['masquees']}/{v['zones']} zones masquées, {v['ignorees']} trop petites ignorées)"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
