#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Exporte les signalements vérifiés de l'équipe en GeoJSON ouvert (ODbL 1.0) — docs/COLLECTE_TERRAIN.md.

    PYTHONPATH=apps/api python scripts/export_signalements_equipe.py --appareils data/communes/ouagadougou/equipe_appareils.txt
    PYTHONPATH=apps/api python scripts/export_signalements_equipe.py --depuis 2026-11-20 --appareils ...

Signalements retenus : envoyés par un téléphone de l'équipe (identifiants Salubri Go listés dans le fichier, un par
ligne), statut « vérifié » ou « nettoyé ». Jamais exporté : identifiant d'appareil, commentaire libre, score
détaillé. Une photo n'est référencée que si le serveur a enregistré son masquage (`reports.masking`).
Écrit data/communes/ouagadougou/signalements_equipe.geojson (dictionnaire : docs/COLLECTE_TERRAIN.md § 5).
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

from salubri_api.db import get_sessionmaker

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/communes/ouagadougou/signalements_equipe.geojson"
LICENCE = "ODbL-1.0"
ATTRIBUTION = "© Équipe Salubri (Hackathon des universités 2026), données sous ODbL 1.0"


def export(devices: list[str], since: str | None, photo_base: str) -> dict:  # type: ignore[type-arg]
    with get_sessionmaker()() as s:
        rows = s.execute(
            text("""
            SELECT r.id, ST_X(r.geom) AS lon, ST_Y(r.geom) AS lat, r.waste_type, r.volume_class, r.reported_at,
                   r.status, r.score, r.gps_accuracy_m, r.masking, q.name AS quartier,
                   (SELECT p.path FROM photos p WHERE p.report_id = r.id LIMIT 1) AS photo
            FROM reports r LEFT JOIN quartiers q ON q.id = r.quartier_id
            WHERE r.device_id = ANY(:dev) AND r.status IN ('verified', 'cleaned')
              AND (CAST(:since AS timestamptz) IS NULL OR r.reported_at >= CAST(:since AS timestamptz))
            ORDER BY r.reported_at"""),
            {"dev": devices, "since": since},
        ).all()
    feats = []
    for r in rows:
        masked = r.masking is not None and r.masking.get("server") is not None
        feats.append(
            {
                "type": "Feature",
                "id": str(r.id),
                "geometry": {"type": "Point", "coordinates": [round(r.lon, 6), round(r.lat, 6)]},
                "properties": {
                    "id": str(r.id),
                    "type_dechet": r.waste_type,
                    "volume": r.volume_class,
                    "date": r.reported_at.astimezone(UTC).isoformat(timespec="minutes"),
                    "statut": r.status,
                    "score": r.score,
                    "precision_gps_m": None if r.gps_accuracy_m is None else round(r.gps_accuracy_m),
                    "quartier": r.quartier,
                    "photo": f"{photo_base}{r.photo}" if (r.photo and masked) else None,
                    "photo_masquee": bool(r.photo and masked),
                },
            }
        )
    return {
        "type": "FeatureCollection",
        "name": "signalements_equipe",
        "licence": LICENCE,
        "attribution": ATTRIBUTION,
        "genere_le": datetime.now(UTC).isoformat(timespec="seconds"),
        "dictionnaire": "docs/COLLECTE_TERRAIN.md#5-dictionnaire-des-données",
        "features": feats,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--appareils", type=Path, required=True, help="identifiants Salubri Go de l'équipe, un par ligne")
    ap.add_argument("--depuis", help="date de début de la campagne (AAAA-MM-JJ)")
    ap.add_argument("--photos", default="/photos/", help="préfixe des liens vers les photos masquées")
    ap.add_argument("--sortie", type=Path, default=OUT)
    a = ap.parse_args()
    devices = [
        line.strip()
        for line in a.appareils.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if not devices:
        print("Aucun identifiant d'appareil dans le fichier", file=sys.stderr)
        return 2
    fc = export(devices, a.depuis, a.photos)
    a.sortie.write_text(json.dumps(fc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n_photos = sum(1 for f in fc["features"] if f["properties"]["photo"])
    print(f"{len(fc['features'])} signalement(s) vérifié(s), {n_photos} photo(s) masquée(s) → {a.sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
