# SPDX-License-Identifier: AGPL-3.0-or-later
from salubri_api.services.params import ValidationThresholds
from salubri_api.services.validation.rules import ReportContext, RuleHit


class R01Duplicate:
    code = "R1"
    title = "Doublon"
    description = (
        "Même type de déchet à moins de 30 m, envoyé par le même appareil sous 72 h, "
        "ou par un autre appareil moins d'une heure plus tard. Deux appareils différents "
        "à plus d'une heure d'écart confirment au lieu de pénaliser."
    )
    penalty = "−40"

    def apply(self, ctx: ReportContext, th: ValidationThresholds) -> RuleHit | None:
        best = None
        for n in ctx.neighbors:
            if n.distance_m > th.duplicate_radius_m or n.waste_type != ctx.waste_type or n.status == "rejected":
                continue
            dt_h = abs((ctx.reported_at - n.reported_at).total_seconds()) / 3600
            same_device = ctx.device_id is not None and n.device_id == ctx.device_id
            if (same_device and dt_h < th.duplicate_window_h) or (not same_device and dt_h < 1):
                if best is None or n.reported_at < best.reported_at:
                    best = n
        if best is None:
            return None
        return RuleHit(
            self.code,
            -40,
            f"Doublon du signalement {best.report_id[:8]} à {best.distance_m:.0f} m",
            duplicate_of=best.report_id,
        )
