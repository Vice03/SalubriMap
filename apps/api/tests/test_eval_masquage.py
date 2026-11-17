# SPDX-License-Identifier: AGPL-3.0-or-later
"""Outils du jeu de mesure du masquage (lot 2.6) : évaluation par taille et par chaîne, aide à l'annotation."""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

import annoter_masquage  # noqa: E402
import eval_masquage  # noqa: E402

FIX = Path(__file__).parent / "fixtures"


def _folder(tmp: Path) -> Path:
    shutil.copy(FIX / "visage_et_plaque.jpg", tmp / "a.jpg")
    shutil.copy(FIX / "petit_visage.jpg", tmp / "b.jpg")
    ann = {
        "images": [
            {
                "fichier": "a.jpg",
                "consentement": "photo NASA, domaine public",
                "zones": [
                    {"type": "visage", "x": 181, "y": 67, "w": 88, "h": 107},
                    {"type": "plaque", "sous_type": "voiture", "x": 842, "y": 197, "w": 182, "h": 69},
                ],
            },
            {
                "fichier": "b.jpg",
                "consentement": "généré",
                "zones": [{"type": "visage", "x": 1700, "y": 500, "w": 36, "h": 46}],
            },
        ]
    }
    (tmp / "annotations.json").write_text(json.dumps(ann), encoding="utf-8")
    return tmp


def test_evaluation_par_chaine_taille_et_sous_type(tmp_path: Path) -> None:
    r = eval_masquage.evaluate(_folder(tmp_path))
    for chain in ("telephone", "telephone_serveur"):
        v = r[chain]["visage"]
        assert v["rappel"] == 1.0 and v["zones"] == 2
        assert v["par_taille"]["moyenne"]["zones"] == 1 and v["par_taille"]["grande"]["zones"] == 1
        assert r[chain]["plaque"]["par_taille"]["moyenne"]["masquees"] == 1
        assert r[chain]["sous_types"]["plaque voiture"]["rappel"] == 1.0
    md = eval_masquage.report(r, "essai")
    assert "Téléphone + seconde passe du serveur" in md and "Petites (< 40 px)" in md


def test_annotation_preremplie_doit_etre_verifiee(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    shutil.copy(FIX / "visage_et_plaque.jpg", tmp_path / "c.jpg")
    assert annoter_masquage.main(["preparer", str(tmp_path)]) == 0
    ann = json.loads((tmp_path / "annotations.json").read_text(encoding="utf-8"))
    assert {z["type"] for z in ann["images"][0]["zones"]} == {"visage", "plaque"}
    assert all(z["a_verifier"] for z in ann["images"][0]["zones"])
    assert annoter_masquage.main(["verifier", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "a_verifier" in out and "au moins 60" in out and "moto" in out
    assert annoter_masquage.main(["floutees", str(tmp_path)]) == 0
    assert (tmp_path / "floutees" / "c.jpg").exists()
