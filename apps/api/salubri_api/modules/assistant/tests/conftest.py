# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixtures communes de Salubri (apps/api/tests/conftest.py : base PostGIS, petite commune synthétique, clients)
réutilisées par les tests du module, plus un client avec le module allumé et un modèle simulé."""

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

_path = Path(__file__).resolve().parents[4] / "tests" / "conftest.py"
_name = "salubri_tests_conftest"
if _name not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_name, _path)
    assert _spec and _spec.loader
    sys.modules[_name] = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(sys.modules[_name])
_base = sys.modules[_name]
globals().update({k: getattr(_base, k) for k in dir(_base) if not k.startswith("__")})

from salubri_api.modules.assistant import models  # noqa: E402,F401  (table du module dans le schéma de test)


@pytest.fixture()
def assistant_on(monkeypatch) -> Iterator[None]:  # type: ignore[no-untyped-def]
    from salubri_api.config import get_settings

    monkeypatch.setattr(get_settings(), "assistant_enabled", True)
    monkeypatch.setattr(get_settings(), "llm_url", "fake:")
    monkeypatch.setattr(get_settings(), "deterministic_solvers", True)
    yield


@pytest.fixture()
def aclient(db, assistant_on):  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    from salubri_api.main import create_app

    with TestClient(create_app(), headers={"X-Salubri-Token": "test-token"}) as c:
        yield c


@pytest.fixture()
def aanon(db, assistant_on):  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    from salubri_api.main import create_app

    with TestClient(create_app()) as c:
        yield c
