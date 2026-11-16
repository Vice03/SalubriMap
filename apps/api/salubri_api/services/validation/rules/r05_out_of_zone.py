# SPDX-License-Identifier: AGPL-3.0-or-later
from salubri_api.services.params import ValidationThresholds
from salubri_api.services.validation.rules import ReportContext, RuleHit


class R05OutOfZone:
    code = "R5"
    title = "Hors de la commune"
    description = "Le point est en dehors des quartiers de la commune (tampon de 500 m)."
    penalty = "rejet"

    def apply(self, ctx: ReportContext, th: ValidationThresholds) -> RuleHit | None:
        if ctx.in_zone:
            return None
        return RuleHit(self.code, -100, "Point hors de la commune", reject=True)
