# SPDX-License-Identifier: AGPL-3.0-or-later
"""The committed rehearsal files are consistent (the full rehearsal runs against a live API: make rehearse)."""

import json
from pathlib import Path

import yaml

from salubri_api.seed.synthetic import photo_for_name

DATA = Path(__file__).resolve().parents[3] / "data" / "rehearsal"


def test_traps_and_expectations_match():
    fc = json.loads((DATA / "traps.geojson").read_text(encoding="utf-8"))
    expected = json.loads((DATA / "traps_expected.json").read_text(encoding="utf-8"))
    ids = [f["properties"]["external_id"] for f in fc["features"]]
    assert len(ids) == len(set(ids)) == len(expected) >= 40
    assert set(ids) == set(expected)
    families = {e["family"].split("-")[0] for e in expected.values()}
    for r in ("r1", "r2", "r5", "r6", "r7", "r8", "r9", "r10", "r11", "r12", "control", "combined"):
        assert r in families
    for f in fc["features"]:
        name = f["properties"].get("photo")
        assert name is None or photo_for_name(name) is not None


def test_scenario_changes_are_well_formed():
    spec = yaml.safe_load((DATA / "scenario_changes.yaml").read_text(encoding="utf-8"))
    actions = {s["action"] for s in spec["steps"]}
    assert {"breakdown", "params", "new_quartier", "double_patch"} <= actions
