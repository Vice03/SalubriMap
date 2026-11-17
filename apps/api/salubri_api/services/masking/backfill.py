# SPDX-License-Identifier: AGPL-3.0-or-later
"""Rattrapage : masque les photos déjà enregistrées (avant le masquage, ou par une ancienne version de l'app).

    python -m salubri_api.services.masking.backfill          # toutes les photos
    python -m salubri_api.services.masking.backfill --dry-run

Chaque fichier est relu, les visages et plaques détectés sont pixellisés, le fichier est réécrit en place.
Le compte du serveur s'ajoute à reports.masking.server. Rejouable : une photo déjà masquée ne bouge plus.
"""

import argparse
import io
import sys

import numpy as np
from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from salubri_api.config import get_settings
from salubri_api.db import get_sessionmaker
from salubri_api.models import Photo, Report
from salubri_api.services.masking.detector import detect, pixelate


def backfill(s: Session, dry_run: bool = False) -> dict[str, int]:
    root = get_settings().photos_dir
    seen = changed = zones = missing = 0
    for ph in s.query(Photo).order_by(Photo.id):
        seen += 1
        path = root / ph.path
        if not path.is_file():
            missing += 1
            continue
        with Image.open(path) as im:
            img = ImageOps.exif_transpose(im).convert("RGB")
        boxes = detect(img)
        if not boxes:
            continue
        changed += 1
        zones += len(boxes)
        if dry_run:
            continue
        arr = np.array(img)
        pixelate(arr, boxes)
        buf = io.BytesIO()
        Image.fromarray(arr).save(buf, "JPEG", quality=85, optimize=True)  # sans EXIF
        path.write_bytes(buf.getvalue())
        rep = s.get(Report, ph.report_id)
        if rep is not None:
            m = dict(rep.masking or {"client": None, "server": 0})
            m["server"] = int(m.get("server") or 0) + len(boxes)
            m["rattrapage"] = True
            rep.masking = m
    if not dry_run:
        s.commit()
    return {"photos": seen, "masquees": changed, "zones": zones, "fichiers_absents": missing}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Masque les visages et plaques des photos déjà enregistrées.")
    p.add_argument("--dry-run", action="store_true", help="compter sans rien réécrire")
    a = p.parse_args(argv)
    with get_sessionmaker()() as s:
        r = backfill(s, a.dry_run)
    verb = "à masquer" if a.dry_run else "masquées"
    print(
        f"{r['photos']} photo(s) relue(s), {r['masquees']} {verb} ({r['zones']} zone(s)), {r['fichiers_absents']} fichier(s) absent(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
