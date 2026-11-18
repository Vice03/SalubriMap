# SPDX-License-Identifier: AGPL-3.0-or-later
from salubri_api.services.params import ValidationThresholds
from salubri_api.services.validation.rules import ReportContext, RuleHit


class R07InWater:
    code = "R7"
    title = "Dans l'eau"
    description = (
        "Le point est dans un plan d'eau ou à moins de 8 m d'un cours d'eau (rivière, marigot, canal). Plan d'eau de "
        "plus d'1 ha : rejet. Les caniveaux et fossés n'en font pas partie : un dépôt dans un caniveau est un vrai cas, "
        "rendu prioritaire."
    )
    penalty = "−45, rejet si plan d'eau > 1 ha"

    def apply(self, ctx: ReportContext, th: ValidationThresholds) -> RuleHit | None:
        if ctx.in_water_area_m2 is not None:
            if ctx.in_water_area_m2 > th.big_water_m2:
                return RuleHit(
                    self.code,
                    -100,
                    f"Point au milieu d'un plan d'eau de {ctx.in_water_area_m2 / 10000:.1f} ha",
                    reject=True,
                )
            return RuleHit(self.code, -45, "Point dans un plan d'eau")
        if ctx.near_waterway:
            return RuleHit(self.code, -45, "Point sur un cours d'eau (moins de 8 m)")
        return None
