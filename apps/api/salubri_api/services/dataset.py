# SPDX-License-Identifier: AGPL-3.0-or-later
"""Which base map is loaded (real OpenStreetMap / Open Buildings, or the synthetic city).

The rehearsal trap set is generated from the loaded map (traps placed in water, in buildings...), so it is
only valid for that map. The key below names the folder data/rehearsal/traps/<key>/ that matches it.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session


def dataset_key(s: Session, commune_id: uuid.UUID) -> str:
    roads_osm = s.execute(
        text("SELECT EXISTS (SELECT 1 FROM roads WHERE commune_id = :c AND osm_id IS NOT NULL)"), {"c": commune_id}
    ).scalar_one()
    blds_synth = s.execute(
        text("SELECT EXISTS (SELECT 1 FROM buildings WHERE commune_id = :c AND source = 'synthetic')"),
        {"c": commune_id},
    ).scalar_one()
    return f"routes-{'osm' if roads_osm else 'synthetiques'}_batiments-{'synthetiques' if blds_synth else 'reels'}"
