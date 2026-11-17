# SPDX-License-Identifier: AGPL-3.0-or-later
import csv
import io

from salubri_api.services.importers.common import KEY_SYNONYMS, Parsed, column_mapping, key_of, normalise
from salubri_api.services.importers.crs import guess, transform_from


def _num(v: object) -> float | None:
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def parse_csv(
    content: bytes, photos: dict[str, bytes], bbox: tuple[float, float, float, float] | None = None
) -> Parsed:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    first = text.splitlines()[0] if text else ""
    delim = ";" if first.count(";") > first.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    if not reader.fieldnames:
        raise ValueError("CSV vide ou sans ligne d'en-tête")
    raw = [dict(r) for r in reader]
    mapping = column_mapping(list(reader.fieldnames))
    field_of = {c: KEY_SYNONYMS.get(c.strip().lower()) or KEY_SYNONYMS.get(key_of(c)) for c in reader.fieldnames}
    xcol = next((c for c, f in field_of.items() if f == "lon"), None)
    ycol = next((c for c, f in field_of.items() if f == "lat"), None)
    note, transform = "WGS 84 (EPSG:4326)", None
    if xcol and ycol:
        xs = [x for r in raw if (x := _num(r.get(xcol))) is not None]
        ys = [y for r in raw if (y := _num(r.get(ycol))) is not None]
        if any(abs(x) > 180 for x in xs) or any(abs(y) > 90 for y in ys):
            epsg = guess(xs, ys, bbox)
            if epsg is None:
                raise ValueError(
                    "Coordonnées en mètres dans aucun système connu autour de la commune : "
                    "convertir le fichier en WGS 84 (EPSG:4326)"
                )
            note, transform = f"EPSG:{epsg} deviné (coordonnées en mètres), converti en WGS 84", transform_from(epsg)
    rows = Parsed(normalise(i, r, photos, transform) for i, r in enumerate(raw, start=1))
    rows.info = {"crs": note, "colonnes": mapping}
    return rows
