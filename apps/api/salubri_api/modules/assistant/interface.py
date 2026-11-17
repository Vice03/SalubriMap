# SPDX-License-Identifier: AGPL-3.0-or-later
"""Seules dépendances du module « Assistant » envers Salubri (à fournir pour le copier dans un autre projet) :

- `settings()` : `assistant_enabled`, `llm_url`, `llm_model`, `llm_api_key`, `llm_timeout_s`, `seasons_enabled` ;
- `Base` (SQLAlchemy), `get_session`, `require_moderateur` (dépendance FastAPI qui rend l'appelant, rôle compris),
  `audit(session, action, entity, entity_id, before, after, actor)` : journal ;
- `DOCS_DIR` : dossier des documents de référence (Markdown) ;
- les lectures existantes appelées par `tools.py` : modèles `PlanVersion`, `Scenario`, `Report`, `DumpSite`,
  `Quartier`, `SimRun`, et le schéma des paramètres `params_schema.json` de la commune.
"""

from pathlib import Path

from salubri_api.config import REPO_ROOT
from salubri_api.config import get_settings as settings  # noqa: F401
from salubri_api.db import get_session  # noqa: F401
from salubri_api.models import Base, DumpSite, PlanVersion, Quartier, Report, Scenario  # noqa: F401
from salubri_api.models.audit import audit  # noqa: F401
from salubri_api.models.sim import SimRun  # noqa: F401
from salubri_api.routers.deps import require_moderateur  # noqa: F401

DOCS_DIR: Path = REPO_ROOT / "docs"
