# SPDX-License-Identifier: AGPL-3.0-or-later
from salubri_api.services.params import ValidationThresholds
from salubri_api.services.validation.rules import ReportContext, RuleHit


class R10Spam:
    code = "R10"
    title = "Envoi en rafale"
    description = "Plus de 10 signalements du même appareil en une heure, ou le même commentaire 5 fois en 24 h."
    penalty = "−30"

    def apply(self, ctx: ReportContext, th: ValidationThresholds) -> RuleHit | None:
        if ctx.device_count_last_hour >= th.spam_per_hour:
            return RuleHit(self.code, -30, f"{ctx.device_count_last_hour + 1} signalements du même appareil en 1 h")
        if ctx.comment and ctx.same_comment_count_24h + 1 >= th.spam_same_comment:
            return RuleHit(
                self.code, -30, f"Commentaire identique envoyé {ctx.same_comment_count_24h + 1} fois en 24 h"
            )
        return None
