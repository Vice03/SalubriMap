# SPDX-License-Identifier: AGPL-3.0-or-later
"""Paramètres documentés : schéma complet, intervalles vérifiés, documentation à jour, import de la mairie."""

import json

import pytest

from salubri_api.config import REPO_ROOT
from salubri_api.models import Commune, Scenario
from salubri_api.params import ParamError, check, diff, load_schema, main, merge, render_doc, validate
from salubri_api.services.params import ScenarioParams, ValidationThresholds

FOLDER = REPO_ROOT / "data" / "communes" / "ouagadougou"
DEFAULTS = json.loads((FOLDER / "params_default.json").read_text(encoding="utf-8"))
SCHEMA = load_schema()


def test_chaque_cle_est_documentee_et_dans_son_intervalle() -> None:
    assert check(DEFAULTS, SCHEMA) == []
    keys = {k for k in DEFAULTS if not k.startswith("_") and k != "validation"}
    assert keys == set(SCHEMA["parametres"])
    assert set(DEFAULTS["validation"]) == set(SCHEMA["validation"])
    for sect in ("parametres", "validation"):
        for k, m in SCHEMA[sect].items():
            assert m["unite"] and m["source"] and m["modeles"] and m["libelle"], k
            val = DEFAULTS[k] if sect == "parametres" else DEFAULTS["validation"][k]
            assert m["defaut"] == val, k


def test_le_json_reste_chargeable_comme_avant() -> None:
    ScenarioParams(**{k: v for k, v in DEFAULTS.items() if k != "validation"})
    ValidationThresholds(**DEFAULTS["validation"])


def test_valeurs_refusees_avec_un_message_en_francais() -> None:
    probs = check(
        {"waste_kg_per_person_day": 7, "season": "hiver", "inconnu": 1, "validation": {"phash_max_hamming": "8"}},
        SCHEMA,
    )
    assert any("waste_kg_per_person_day" in p and "hors de l'intervalle plausible" in p for p in probs)
    assert any("valeurs possibles" in p for p in probs)
    assert any("paramètre inconnu" in p for p in probs)
    assert any("un nombre est attendu" in p for p in probs)
    with pytest.raises(ParamError, match="Paramètres refusés"):
        validate({"walk_distance_max_m": 5})


def test_documentation_generee_a_jour() -> None:
    assert (REPO_ROOT / "docs" / "PARAMETRES.md").read_text(encoding="utf-8") == render_doc(SCHEMA, DEFAULTS)


def test_diff_et_fusion() -> None:
    old = {"budget_fcfa_month": 1.0, "validation": {"a": 1, "b": 2}}
    new = {"budget_fcfa_month": 2.0, "validation": {"b": 3}}
    assert diff(old, new) == [("budget_fcfa_month", 1.0, 2.0), ("validation.b", 2, 3)]
    assert merge(old, new) == {"budget_fcfa_month": 2.0, "validation": {"a": 1, "b": 3}}


def test_import_mairie_une_commande(client, tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    from salubri_api.db import get_sessionmaker

    f = tmp_path / "mairie.json"
    f.write_text(json.dumps({"budget_fcfa_month": 31_000_000, "validation": {"duplicate_radius_m": 25}}), "utf-8")
    assert main(["import", str(f), "--a-blanc", "--commune", "testville"]) == 0
    assert "budget_fcfa_month" in capsys.readouterr().out
    assert main(["import", str(f), "--simulation", "--commune", "testville"]) == 0
    with get_sessionmaker()() as s:
        c = s.query(Commune).filter(Commune.slug == "testville").one()
        assert c.params_default["budget_fcfa_month"] == 31_000_000
        assert c.params_default["validation"]["duplicate_radius_m"] == 25
        assert c.params_default["validation"]["phash_max_hamming"] == 8  # le reste est gardé
        base = s.query(Scenario).filter(Scenario.is_baseline.is_(True)).one()
        assert base.params["budget_fcfa_month"] == 31_000_000
    bad = tmp_path / "faux.json"
    bad.write_text(json.dumps({"budget_fcfa_month": -5}), "utf-8")
    assert main(["import", str(bad), "--commune", "testville"]) == 1
    assert "hors de l'intervalle plausible" in capsys.readouterr().err
