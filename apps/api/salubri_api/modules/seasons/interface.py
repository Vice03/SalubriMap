# SPDX-License-Identifier: AGPL-3.0-or-later
"""Seules dépendances du module « Saisons » envers Salubri. Pour copier le module dans un autre projet FastAPI,
fournir ces noms (mêmes signatures) et rien d'autre.

- `Base` : base déclarative SQLAlchemy ; `Road` : table des routes (id, commune_id, osm_id, geom LINESTRING 4326,
  highway) ; `Report` : signalements (id, geom, status, rule_hits) ; `Commune` (id, slug).
- `get_session`, `get_commune`, `require_moderateur` : dépendances FastAPI (session, commune courante, droit
  d'écriture des modérateurs) ; `audit(session, action, entity, entity_id, before, after)` : journal.
- `stage_report(session, commune, ReportIn, photo)` et `validate_staged(session, commune, [staged])` : création
  d'un signalement avec ses règles de validation et son masquage ; `ReportIn` : son schéma.
- `settings()` : réglages (`seasons_enabled`, `data_dir`).
"""

from salubri_api.config import get_settings as settings  # noqa: F401
from salubri_api.db import get_session  # noqa: F401
from salubri_api.models import Base, Commune, Report, Road  # noqa: F401
from salubri_api.models.audit import audit  # noqa: F401
from salubri_api.routers.deps import get_commune, require_moderateur  # noqa: F401


def report_tools():  # type: ignore[no-untyped-def]
    """Import tardif (évite un cycle) : création et validation d'un signalement."""
    from salubri_api.schemas.reports import ReportIn
    from salubri_api.services.reports import stage_report, validate_staged

    return ReportIn, stage_report, validate_staged
