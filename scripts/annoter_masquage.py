#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Aide à l'annotation du jeu de mesure du masquage (data/eval/masquage/README.md).

    PYTHONPATH=apps/api python scripts/annoter_masquage.py preparer data/eval/masquage
    PYTHONPATH=apps/api python scripts/annoter_masquage.py verifier data/eval/masquage
    PYTHONPATH=apps/api python scripts/annoter_masquage.py floutees data/eval/masquage

- preparer : crée ou complète `annotations.json` : une entrée par photo, zones pré-remplies par le détecteur et
  marquées `"a_verifier": true`. Les annotateurs corrigent (déplacer, ajouter les oubliés, supprimer les faux,
  `sous_type` « moto »/« voiture » pour les plaques) puis retirent la marque. Les entrées déjà vérifiées ne sont
  jamais réécrites. **Pré-remplir n'est pas mesurer** : tant qu'une zone garde `a_verifier`, `verifier` refuse.
- verifier : contrôle le format, le consentement et les nombres minimaux (60 photos, 40 plaques dont des motos).
- floutees : écrit `floutees/<photo>` avec toutes les zones annotées pixellisées : ce sont ces copies (et
  `annotations.json`) qui sont versionnées ; les originaux restent hors du dépôt (.gitignore).
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from salubri_api.services.masking.detector import Box, detect, pixelate

EXT = (".jpg", ".jpeg", ".png")


def _load(folder: Path) -> dict:
    f = folder / "annotations.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"images": []}


def _save(folder: Path, ann: dict) -> None:
    (folder / "annotations.json").write_text(json.dumps(ann, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _open(path: Path) -> Image.Image:
    with Image.open(path) as im:
        return ImageOps.exif_transpose(im).convert("RGB")


def preparer(folder: Path) -> int:
    ann = _load(folder)
    known = {i["fichier"] for i in ann["images"]}
    added = 0
    for p in sorted(folder.iterdir()):
        if p.suffix.lower() not in EXT or p.name in known:
            continue
        zones = [
            {"type": b.kind, "x": round(b.x), "y": round(b.y), "w": round(b.w), "h": round(b.h), "a_verifier": True}
            for b in detect(_open(p))
        ]
        ann["images"].append({"fichier": p.name, "consentement": "", "zones": zones})
        added += 1
    _save(folder, ann)
    print(f"{added} photo(s) ajoutée(s), zones pré-remplies à vérifier ; {len(ann['images'])} au total")
    return 0


def verifier(folder: Path) -> int:
    ann, problems = _load(folder), []
    imgs = ann["images"]
    for i in imgs:
        if not (folder / i["fichier"]).exists():
            problems.append(f"{i['fichier']} : photo absente")
        if not i.get("consentement"):
            problems.append(f"{i['fichier']} : consentement non renseigné")
        for z in i["zones"]:
            if z.get("a_verifier"):
                problems.append(f"{i['fichier']} : zone {z['type']} encore « a_verifier »")
            if z["type"] not in ("visage", "plaque") or min(z["w"], z["h"]) <= 0:
                problems.append(f"{i['fichier']} : zone invalide {z}")
    plates = [z for i in imgs for z in i["zones"] if z["type"] == "plaque"]
    motos = [z for z in plates if z.get("sous_type") == "moto"]
    if len(imgs) < 60:
        problems.append(f"{len(imgs)} photos : il en faut au moins 60")
    if len(plates) < 40:
        problems.append(f"{len(plates)} plaques : il en faut au moins 40")
    if not motos:
        problems.append("aucune plaque de moto annotée (sous_type « moto »)")
    for p in problems:
        print(p)
    print("OK" if not problems else f"{len(problems)} problème(s)")
    return 1 if problems else 0


def floutees(folder: Path) -> int:
    out = folder / "floutees"
    out.mkdir(exist_ok=True)
    n = 0
    for i in _load(folder)["images"]:
        img = _open(folder / i["fichier"])
        arr = np.array(img)
        pixelate(arr, [Box(z["x"], z["y"], z["w"], z["h"], z["type"], 1.0) for z in i["zones"]])
        Image.fromarray(arr).save(out / Path(i["fichier"]).with_suffix(".jpg").name, "JPEG", quality=85)
        n += 1
    print(f"{n} copie(s) floutée(s) dans {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=("preparer", "verifier", "floutees"))
    ap.add_argument("dossier", type=Path)
    a = ap.parse_args(argv)
    return {"preparer": preparer, "verifier": verifier, "floutees": floutees}[a.action](a.dossier)


if __name__ == "__main__":
    sys.exit(main())
