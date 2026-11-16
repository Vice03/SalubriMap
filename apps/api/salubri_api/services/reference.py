# SPDX-License-Identifier: AGPL-3.0-or-later
"""Données de référence officielles (SDGD Ouagadougou 2020) : CCT existants et décharges relevées.

Fichier : data/communes/<slug>/sdgd2020.geojson (sites numérisés, précision ± 500 m, voir docs/HYPOTHESES.md).
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from salubri_api.config import get_settings

DUMP_STATUTS = ("decharge_sauvage", "decharge_encadree", "autre")


@lru_cache(maxsize=8)
def _load(path: str, mtime: float) -> list[dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8")).get("features", [])


def sdgd_features(slug: str) -> list[dict[str, Any]]:
    p = get_settings().data_dir / "communes" / slug / "sdgd2020.geojson"
    if not p.exists():
        return []
    return _load(str(p), p.stat().st_mtime)


def existing_cct(slug: str) -> list[tuple[str, float, float]]:
    """(clé, lon, lat) des centres de collecte et de tri existants."""
    out = []
    for f in sdgd_features(slug):
        if f["properties"].get("statut") == "cct":
            lon, lat = f["geometry"]["coordinates"][:2]
            out.append(("CCT-" + f["properties"]["id"].split("-")[-1], float(lon), float(lat)))
    return out
