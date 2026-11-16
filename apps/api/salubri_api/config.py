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
    commune: str = "ouagadougou"
    # Origines autorisées en cross-origin ; vide = même origine seulement (nginx sert l'UI et l'API ensemble).
    cors_origins: str = ""
    # Code d'accès « mairie » exigé (en-tête X-Salubri-Token) sur toutes les écritures sauf l'envoi d'un
    # signalement citoyen. Vide = contrôle désactivé (développement local uniquement).
    admin_token: str = ""
    reports_debounce_s: float = 2.0
    auto_recompute: bool = True
    # au démarrage, relancer les recalculs interrompus par un redémarrage (désactivé dans les tests)
    resume_on_startup: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
