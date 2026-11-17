# SPDX-License-Identifier: AGPL-3.0-or-later
"""Application settings, read from environment variables (prefix SALUBRI_)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SALUBRI_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://salubri:salubri@localhost:5432/salubri"
    osrm_url: str = "http://localhost:5000"
    osrm_rain_url: str = "http://localhost:5001"
    osrm_timeout_s: float = 1.5
    data_dir: Path = REPO_ROOT / "data"
    photos_dir: Path = REPO_ROOT / "var" / "photos"
    # modèles ONNX du masquage, partagés avec Salubri Go (docker-compose les monte en lecture seule)
    masking_models_dir: Path = REPO_ROOT / "apps" / "go" / "public" / "models"
    commune: str = "ouagadougou"
    # Origines autorisées en cross-origin ; vide = même origine seulement (nginx sert l'UI et l'API ensemble).
    cors_origins: str = ""
    # Code d'accès « mairie » exigé (en-tête X-Salubri-Token) sur toutes les écritures sauf l'envoi d'un
    # signalement citoyen. Vide = contrôle désactivé (développement local uniquement).
    admin_token: str = ""
    # Mode démonstration (jury, répétitions) : compte « demo » et code « ouaga2026 » connus de tous, badge
    # visible dans l'interface. Hors démonstration (false), l'API refuse de démarrer avec un secret par défaut.
    # Faux par défaut (sûr) ; docker-compose.yml l'active pour que la démo reste « une commande ».
    demo_mode: bool = False
    # Clé de signature des sessions (connexion des comptes mairie). Vide = clé aléatoire tirée au démarrage :
    # les sessions ouvertes ne survivent pas à un redémarrage de l'API (il suffit de se reconnecter).
    secret_key: str = ""
    session_hours: float = 8.0
    reports_debounce_s: float = 2.0
    auto_recompute: bool = True
    # au démarrage, relancer les recalculs interrompus par un redémarrage (désactivé dans les tests)
    resume_on_startup: bool = True


DEMO_TOKEN = "ouaga2026"


def service_token(s: "Settings") -> str:
    """Code de service effectif : SALUBRI_ADMIN_TOKEN, ou le code de démonstration en mode démo."""
    return s.admin_token or (DEMO_TOKEN if s.demo_mode else "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
