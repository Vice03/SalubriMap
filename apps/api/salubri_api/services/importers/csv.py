# SPDX-License-Identifier: AGPL-3.0-or-later
import csv
import io

from salubri_api.services.importers.common import ParsedRow, normalise


def parse_csv(content: bytes, photos: dict[str, bytes]) -> list[ParsedRow]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    first = text.splitlines()[0] if text else ""
    delim = ";" if first.count(";") > first.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    if not reader.fieldnames:
        raise ValueError("CSV vide ou sans ligne d'en-tête")
    return [normalise(i, dict(r), photos) for i, r in enumerate(reader, start=1)]
