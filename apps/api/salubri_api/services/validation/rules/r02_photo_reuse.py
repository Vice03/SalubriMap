# SPDX-License-Identifier: AGPL-3.0-or-later
from salubri_api.services.params import ValidationThresholds
from salubri_api.services.validation.rules import ReportContext, RuleHit


class R02PhotoReuse:
    code = "R2"
    title = "Photo réutilisée"
    description = "Photo identique (SHA-256) ou presque identique (pHash, Hamming ≤ 8) à celle d'un autre signalement."
    penalty = "−70 identique, −50 similaire"

    def apply(self, ctx: ReportContext, th: ValidationThresholds) -> RuleHit | None:
        if ctx.photo_same_sha:
            return RuleHit(self.code, -70, f"Photo identique à celle du signalement {ctx.photo_same_sha[:8]}")
        if ctx.photo_similar and ctx.photo_similar[1] <= th.phash_max_hamming:
            rid, dist = ctx.photo_similar
            return RuleHit(self.code, -50, f"Photo quasi identique au signalement {rid[:8]} (écart {dist}/64)")
        return None
