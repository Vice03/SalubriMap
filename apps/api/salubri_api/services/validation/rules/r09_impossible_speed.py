# SPDX-License-Identifier: AGPL-3.0-or-later
from salubri_api.services.geo import haversine_m
from salubri_api.services.params import ValidationThresholds
from salubri_api.services.validation.rules import ReportContext, RuleHit


class R09ImpossibleSpeed:
    code = "R9"
    title = "Déplacement impossible"
    description = "Le même appareil aurait dû se déplacer à plus de 120 km/h depuis son signalement précédent."
    penalty = "−40"

    def apply(self, ctx: ReportContext, th: ValidationThresholds) -> RuleHit | None:
        if ctx.previous_by_device is None:
            return None
        plat, plon, pat = ctx.previous_by_device
        d_m = haversine_m(ctx.lat, ctx.lon, plat, plon)
        dt_s = abs((ctx.reported_at - pat).total_seconds())
        if d_m < 200:
            return None
        speed = (d_m / 1000) / max(dt_s / 3600, 1 / 3600)
        if speed > th.max_speed_kmh:
            return RuleHit(self.code, -40, f"{d_m / 1000:.1f} km en {dt_s / 60:.0f} min, soit {speed:.0f} km/h")
        return None
