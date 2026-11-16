# SPDX-License-Identifier: AGPL-3.0-or-later
import json

from salubri_api.services.importers.common import ParsedRow, normalise


def parse_geojson(content: bytes, photos: dict[str, bytes]) -> list[ParsedRow]:
    try:
        doc = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"GeoJSON illisible : {exc}") from exc
    feats = doc.get("features") if isinstance(doc, dict) and doc.get("type") == "FeatureCollection" else None
    if feats is None:
        raise ValueError("Le fichier doit être une FeatureCollection GeoJSON")
    rows: list[ParsedRow] = []
    for i, f in enumerate(feats, start=1):
        geom = (f or {}).get("geometry") or {}
        props = dict((f or {}).get("properties") or {})
        if geom.get("type") != "Point" or not isinstance(geom.get("coordinates"), list) or len(geom["coordinates"]) < 2:
            rows.append(ParsedRow(i, None, None, ["Géométrie absente ou non ponctuelle (Point attendu)"]))
            continue
        props["lon"], props["lat"] = geom["coordinates"][0], geom["coordinates"][1]
        if "id" in f and "external_id" not in props:
            props["external_id"] = f["id"]
        rows.append(normalise(i, props, photos))
    return rows
