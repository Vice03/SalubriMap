# SPDX-License-Identifier: AGPL-3.0-or-later
from salubri_api.services.params import ValidationThresholds
from salubri_api.services.validation.rules import ReportContext, RuleHit


class R04ExifDate:
    code = "R4"
    title = "Photo ancienne"
    description = "La date de prise de vue de la photo est à plus de 30 jours de la date du signalement."
    penalty = "−20"

    def apply(self, ctx: ReportContext, th: ValidationThresholds) -> RuleHit | None:
        p = ctx.photo
        if p is None or p.exif_taken_at is None:
            return None
        days = abs((ctx.reported_at - p.exif_taken_at).total_seconds()) / 86400
        if days > th.exif_max_age_days:
            return RuleHit(self.code, -20, f"Photo prise le {p.exif_taken_at:%d/%m/%Y}, {days:.0f} jours avant")
        return None
