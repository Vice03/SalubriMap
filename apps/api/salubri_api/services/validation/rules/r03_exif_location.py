# SPDX-License-Identifier: AGPL-3.0-or-later
from salubri_api.services.geo import haversine_m
from salubri_api.services.params import ValidationThresholds
from salubri_api.services.validation.rules import ReportContext, RuleHit


class R03ExifLocation:
    code = "R3"
    title = "Photo prise ailleurs"
    description = "La position GPS enregistrée dans la photo est à plus de 500 m de la position déclarée."
    penalty = "−30"

    def apply(self, ctx: ReportContext, th: ValidationThresholds) -> RuleHit | None:
        p = ctx.photo
        if p is None or p.exif_lat is None or p.exif_lon is None:
            return None
        d = haversine_m(ctx.lat, ctx.lon, p.exif_lat, p.exif_lon)
        if d > th.exif_gps_max_m:
            return RuleHit(self.code, -30, f"Photo géolocalisée à {d / 1000:.1f} km du point déclaré")
        return None
