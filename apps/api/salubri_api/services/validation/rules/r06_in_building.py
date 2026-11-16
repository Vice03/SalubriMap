# SPDX-License-Identifier: AGPL-3.0-or-later
from salubri_api.services.params import ValidationThresholds
from salubri_api.services.validation.rules import ReportContext, RuleHit


class R06InBuilding:
    code = "R6"
    title = "Dans un bâtiment"
    description = "Le point tombe à l'intérieur d'un bâtiment Open Buildings (confiance ≥ 0,7)."
    penalty = "−35 (≥ 40 m²), −50 (≥ 200 m²)"

    def apply(self, ctx: ReportContext, th: ValidationThresholds) -> RuleHit | None:
        a = ctx.building_area_m2
        if a is None or a < th.building_small_m2:
            return None
        delta = -50 if a >= th.building_large_m2 else -35
        return RuleHit(self.code, delta, f"Point dans un bâtiment de {a:.0f} m²")
