# SPDX-License-Identifier: AGPL-3.0-or-later
from salubri_api.services.params import ValidationThresholds
from salubri_api.services.validation.rules import ReportContext, RuleHit


def _decimals(x: float) -> int:
    s = f"{abs(x):.7f}".rstrip("0")
    return len(s.split(".")[1]) if "." in s else 0


class R08FakeGps:
    code = "R8"
    title = "GPS suspect"
    description = (
        "Coordonnées (0,0) ou hors plage : rejet. Coordonnées arrondies (≤ 3 décimales) : −25. "
        "Même point au mètre près qu'un autre appareil : −40. Précision > 150 m : −15."
    )
    penalty = "rejet / −25 / −40 / −15"

    def apply(self, ctx: ReportContext, th: ValidationThresholds) -> RuleHit | None:
        if (abs(ctx.lat) < 1e-6 and abs(ctx.lon) < 1e-6) or not (-90 <= ctx.lat <= 90 and -180 <= ctx.lon <= 180):
            return RuleHit(self.code, -100, "Coordonnées impossibles (0,0 ou hors plage)", reject=True)
        delta, details = 0, []
        if ctx.same_point_other_device:
            delta -= 40
            details.append(f"même point exact que le signalement {ctx.same_point_other_device[:8]} d'un autre appareil")
        if _decimals(ctx.lat) <= 3 and _decimals(ctx.lon) <= 3:
            delta -= 25
            details.append("coordonnées arrondies (saisie manuelle probable)")
        if ctx.accuracy_m is not None and ctx.accuracy_m > th.gps_accuracy_max_m:
            delta -= 15
            details.append(f"précision GPS de {ctx.accuracy_m:.0f} m")
        if delta == 0:
            return None
        return RuleHit(self.code, delta, "; ".join(details).capitalize())
