# SPDX-License-Identifier: AGPL-3.0-or-later
"""Systèmes de coordonnées des fichiers importés : déclaré (membre `crs` du GeoJSON) ou deviné (coordonnées en
mètres), toujours ramené en WGS 84 (pyproj, MIT)."""

import re
from statistics import median

from pyproj import CRS, Transformer
from pyproj.exceptions import CRSError

from salubri_api.services.importers.common import Transform

WGS84 = {4326, None}
# candidats essayés quand un fichier donne des mètres sans dire lesquels (Burkina Faso : UTM 30N et 31N,
# Web Mercator des exports de cartes en ligne)
GUESSES = [32630, 32631, 3857]


def epsg_of(name: str) -> int | None:
    """« EPSG:32630 », « urn:ogc:def:crs:EPSG::32630 », « urn:ogc:def:crs:OGC:1.3:CRS84 » → code EPSG."""
    s = str(name).strip()
    if s.upper().endswith("CRS84"):
        return 4326
    m = re.search(r"EPSG:+(\d+)", s, re.IGNORECASE)
    if m:
        return int(m.group(1))
    try:
        return CRS.from_user_input(s).to_epsg()
    except CRSError as exc:
        raise ValueError(
            f"Système de coordonnées « {name} » inconnu : convertir le fichier en WGS 84 (EPSG:4326)"
        ) from exc


def transform_from(epsg: int) -> Transform:
    try:
        tr = Transformer.from_crs(epsg, 4326, always_xy=True)
    except CRSError as exc:
        raise ValueError(f"Système de coordonnées EPSG:{epsg} inconnu : convertir le fichier en WGS 84") from exc

    def f(x: float, y: float) -> tuple[float, float]:
        lon, lat = tr.transform(x, y)
        return float(lon), float(lat)

    return f


def guess(xs: list[float], ys: list[float], bbox: tuple[float, float, float, float] | None) -> int | None:
    """Coordonnées en mètres : le système qui met le centre du fichier près de la commune (0,5° de marge)."""
    if bbox is None or not xs:
        return None
    x, y = median(xs), median(ys)
    for code in GUESSES:
        lon, lat = transform_from(code)(x, y)
        if bbox[0] - 0.5 <= lon <= bbox[2] + 0.5 and bbox[1] - 0.5 <= lat <= bbox[3] + 0.5:
            return code
    return None
