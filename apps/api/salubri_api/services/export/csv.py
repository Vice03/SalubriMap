# SPDX-License-Identifier: AGPL-3.0-or-later
import csv
import io

from salubri_api.models import DumpSite
from salubri_api.services.geo import shape

COLUMNS = [
    "id",
    "lat",
    "lon",
    "status",
    "waste_type",
    "volume_est_m3",
    "n_reports",
    "first_reported_at",
    "last_reported_at",
    "near_water",
    "near_drain",
    "priority",
    "confidence",
]


def dump_sites_csv(sites: list[DumpSite]) -> str:
    buf = io.StringIO()
    buf.write("﻿")  # BOM: Excel opens UTF-8 correctly
    w = csv.writer(buf, delimiter=";")
    w.writerow(COLUMNS)
    for d in sites:
        g = shape(d.geom)
        w.writerow(
            [
                d.id,
                f"{g.y:.6f}",
                f"{g.x:.6f}",
                d.status,
                d.dominant_type,
                d.volume_est_m3,
                d.n_reports,
                d.first_reported_at.isoformat(),
                d.last_reported_at.isoformat(),
                d.near_water,
                bool(d.near_drain),
                d.priority,
                d.mean_score,
            ]
        )
    return buf.getvalue()
