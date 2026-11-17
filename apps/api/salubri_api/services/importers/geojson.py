# SPDX-License-Identifier: AGPL-3.0-or-later
import json

from salubri_api.services.importers.common import Parsed, ParsedRow, column_mapping, normalise
from salubri_api.services.importers.crs import WGS84, epsg_of, guess, transform_from


def parse_geojson(
    content: bytes, photos: dict[str, bytes], bbox: tuple[float, float, float, float] | None = None
) -> Parsed:
    try:
        doc = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"GeoJSON illisible : {exc}") from exc
    feats = doc.get("features") if isinstance(doc, dict) and doc.get("type") == "FeatureCollection" else None
    if feats is None:
        raise ValueError("Le fichier doit être une FeatureCollection GeoJSON")
    declared = ((doc.get("crs") or {}).get("properties") or {}).get("name")
    epsg = epsg_of(declared) if declared else None
    pts = [
        f["geometry"]["coordinates"][:2]
        for f in feats
        if isinstance(f, dict)
        and isinstance(f.get("geometry"), dict)
        and f["geometry"].get("type") == "Point"
        and isinstance(f["geometry"].get("coordinates"), list)
        and len(f["geometry"]["coordinates"]) >= 2
        and all(isinstance(c, int | float) for c in f["geometry"]["coordinates"][:2])
    ]
    note = "WGS 84 (EPSG:4326)"
    if epsg is None and pts and any(abs(x) > 180 or abs(y) > 90 for x, y in pts):
        epsg = guess([p[0] for p in pts], [p[1] for p in pts], bbox)
        if epsg is None:
            raise ValueError(
                "Coordonnées en mètres sans membre « crs » et dans aucun système connu autour de la commune : "
                "convertir le fichier en WGS 84 (EPSG:4326)"
            )
        note = f"EPSG:{epsg} deviné (coordonnées en mètres), converti en WGS 84"
    elif epsg not in WGS84:
        note = f"EPSG:{epsg} déclaré, converti en WGS 84"
    transform = transform_from(epsg) if epsg not in WGS84 else None
    rows = Parsed()
    cols: set[str] = set()
    for i, f in enumerate(feats, start=1):
        geom = (f or {}).get("geometry") or {}
        props = dict((f or {}).get("properties") or {})
        cols.update(props)
        if geom.get("type") != "Point" or not isinstance(geom.get("coordinates"), list) or len(geom["coordinates"]) < 2:
            rows.append(ParsedRow(i, None, None, ["Géométrie absente ou non ponctuelle (Point attendu)"]))
            continue
        props["lon"], props["lat"] = geom["coordinates"][0], geom["coordinates"][1]
        if "id" in f and "external_id" not in props:
            props["external_id"] = f["id"]
        rows.append(normalise(i, props, photos, transform))
    rows.info = {"crs": note, "colonnes": column_mapping(sorted(cols))}
    return rows
