# SPDX-License-Identifier: AGPL-3.0-or-later
"""Module « Assistant » : un modèle de langue local explique plans et simulations, en lecture seule.

Éteint par défaut (`SALUBRI_ASSISTANT_ENABLED=false`) ; sans serveur de modèle local, il répond « assistant
indisponible » et rien d'autre n'est touché. Voir README.md.
"""


def enabled() -> bool:
    from salubri_api.modules.assistant.interface import settings

    return bool(settings().assistant_enabled)
