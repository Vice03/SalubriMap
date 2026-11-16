# SPDX-License-Identifier: AGPL-3.0-or-later
from salubri_api.services.params import ValidationThresholds
from salubri_api.services.validation.rules import ReportContext, RuleHit


class R11UninformativePhoto:
    code = "R11"
    title = "Photo inexploitable"
    description = "Photo trop uniforme (écran noir, mur uni) ou trop petite (moins de 200 px)."
    penalty = "−20"

    def apply(self, ctx: ReportContext, th: ValidationThresholds) -> RuleHit | None:
        p = ctx.photo
        if p is None:
            return None
        if min(p.width, p.height) < th.photo_min_side_px:
            return RuleHit(self.code, -20, f"Photo trop petite ({p.width}×{p.height} px)")
        if p.luminance_var < th.luminance_var_min:
            return RuleHit(self.code, -20, "Photo uniforme, rien n'y est visible")
        return None
