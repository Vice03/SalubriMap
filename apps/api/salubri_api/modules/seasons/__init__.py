# SPDX-License-Identifier: AGPL-3.0-or-later
"""Module « Saisons » : points de regroupement et tournées qui suivent l'état des routes selon la saison.

Éteint par défaut (`SALUBRI_SEASONS_ENABLED=false`). Éteint, ou allumé avec une table `road_conditions` vide, il
ne change rien. Voir README.md.
"""


def enabled() -> bool:
    from salubri_api.modules.seasons.interface import settings

    return bool(settings().seasons_enabled)
