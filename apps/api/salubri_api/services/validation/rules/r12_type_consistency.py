# SPDX-License-Identifier: AGPL-3.0-or-later
from salubri_api.services.params import ValidationThresholds
from salubri_api.services.validation.rules import ReportContext, RuleHit


class R12TypeConsistency:
    code = "R12"
    title = "Description incohérente"
    description = (
        "Volume « camion » ou plus avec une photo très légère, ou déchets biomédicaux "
        "à plus de 300 m de tout établissement de santé. Indicatif."
    )
    penalty = "−10"

    def apply(self, ctx: ReportContext, th: ValidationThresholds) -> RuleHit | None:
        if (
            ctx.volume_class in ("truck", "more")
            and ctx.photo is not None
            and ctx.photo.bytes < th.truck_photo_min_bytes
        ):
            return RuleHit(self.code, -10, f"Volume « {ctx.volume_class} » mais photo de {ctx.photo.bytes // 1000} Ko")
        if ctx.waste_type == "medical" and not ctx.near_medical_poi:
            return RuleHit(self.code, -10, "Déchets biomédicaux loin de tout établissement de santé")
        return None
