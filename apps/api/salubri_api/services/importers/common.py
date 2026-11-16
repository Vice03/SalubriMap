# SPDX-License-Identifier: AGPL-3.0-or-later
"""Normalisation shared by the GeoJSON and CSV importers: synonyms, dates, swapped coordinates, photos."""

import base64
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from salubri_api.schemas.reports import ReportIn

WASTE_SYNONYMS = {
    "household": "household",
    "menager": "household",
    "ménager": "household",
    "ordures": "household",
    "plastic": "plastic",
    "plastique": "plastic",
    "rubble": "rubble",
    "gravats": "rubble",
    "gravat": "rubble",
    "organic": "organic",
    "organique": "organic",
    "vert": "organic",
    "medical": "medical",
    "médical": "medical",
    "biomedical": "medical",
    "biomédical": "medical",
    "mixed": "mixed",
    "mixte": "mixed",
    "other": "other",
    "autre": "other",
}
VOLUME_SYNONYMS = {
    "bag": "bag",
    "sac": "bag",
    "wheelbarrow": "wheelbarrow",
    "brouette": "wheelbarrow",
    "cart": "cart",
    "charrette": "cart",
    "truck": "truck",
    "camion": "truck",
    "more": "more",
    "plus": "more",
}
KEY_SYNONYMS = {
    "latitude": "lat",
    "y": "lat",
    "lat": "lat",
    "longitude": "lon",
    "lng": "lon",
    "long": "lon",
    "x": "lon",
    "lon": "lon",
    "type": "waste_type",
    "waste_type": "waste_type",
    "type_dechet": "waste_type",
    "volume": "volume_class",
    "volume_class": "volume_class",
    "date": "reported_at",
    "reported_at": "reported_at",
    "datetime": "reported_at",
    "comment": "comment",
    "commentaire": "comment",
    "description": "comment",
    "device_id": "device_id",
    "appareil": "device_id",
    "photo": "photo",
    "photo_path": "photo",
    "image": "photo",
    "external_id": "external_id",
    "id": "external_id",
    "accuracy": "accuracy",
    "precision": "accuracy",
    "gps_accuracy_m": "accuracy",
}
FR_DATE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$")


@dataclass
class ParsedRow:
    row: int
    data: ReportIn | None
    photo_bytes: bytes | None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_date(v: Any) -> datetime:
    s = str(v).strip()
    m = FR_DATE.match(s)
    if m:
        d, mo, y, hh, mm, ss = m.groups()
        return datetime(int(y), int(mo), int(d), int(hh or 0), int(mm or 0), int(ss or 0), tzinfo=UTC)
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _photo(value: Any, photos: dict[str, bytes]) -> tuple[bytes | None, str | None]:
    if not value:
        return None, None
    s = str(value)
    if s.startswith("data:"):
        try:
            return base64.b64decode(s.split(",", 1)[1]), None
        except Exception:
            return None, "Photo en base64 illisible"
    name = s.replace("\\", "/").split("/")[-1]
    if name in photos:
        return photos[name], None
    return None, f"Photo « {name} » absente de l'archive : signalement importé sans photo"


def normalise(row_no: int, raw: dict[str, Any], photos: dict[str, bytes]) -> ParsedRow:
    vals: dict[str, Any] = {}
    for k, v in raw.items():
        key = KEY_SYNONYMS.get(str(k).strip().lower())
        if key and v not in (None, ""):
            vals[key] = v.strip() if isinstance(v, str) else v
    errors: list[str] = []
    warnings: list[str] = []
    if "lat" not in vals or "lon" not in vals:
        return ParsedRow(row_no, None, None, ["Coordonnées manquantes (lat/lon)"])
    try:
        lat, lon = float(str(vals["lat"]).replace(",", ".")), float(str(vals["lon"]).replace(",", "."))
    except ValueError:
        return ParsedRow(row_no, None, None, ["Coordonnées non numériques"])
    if -5 <= lat <= 0 and 10 <= lon <= 14:
        lat, lon = lon, lat
        warnings.append("coords_swapped : latitude et longitude inversées, corrigées automatiquement")
    if "waste_type" in vals:
        wt = WASTE_SYNONYMS.get(str(vals["waste_type"]).lower())
        if wt is None:
            warnings.append(f"Type « {vals['waste_type']} » inconnu, remplacé par « other »")
            wt = "other"
        vals["waste_type"] = wt
    if "volume_class" in vals:
        vc = VOLUME_SYNONYMS.get(str(vals["volume_class"]).lower())
        if vc is None:
            warnings.append(f"Volume « {vals['volume_class']} » inconnu, remplacé par « bag »")
            vc = "bag"
        vals["volume_class"] = vc
    if "reported_at" in vals:
        try:
            vals["reported_at"] = parse_date(vals["reported_at"])
        except ValueError:
            return ParsedRow(
                row_no, None, None, [f"Date invalide : « {vals['reported_at']} » (attendu ISO 8601 ou JJ/MM/AAAA)"]
            )
    photo_bytes, perr = _photo(vals.pop("photo", None), photos)
    if perr:
        warnings.append(perr)
    for k in ("external_id", "device_id", "comment"):
        if k in vals:
            vals[k] = str(vals[k])
    try:
        data = ReportIn(lat=lat, lon=lon, **{k: v for k, v in vals.items() if k not in ("lat", "lon")})
    except ValidationError as exc:
        errors = [f"{'.'.join(str(x) for x in e['loc'])} : {e['msg']}" for e in exc.errors()]
        return ParsedRow(row_no, None, None, errors, warnings)
    return ParsedRow(row_no, data, photo_bytes, errors, warnings)
