# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mode « reel » : les signalements d'exemple partent, ceux de Salubri Go et du SDGD restent ; retour à « demo »
sans rien perdre de réel."""

from shapely.geometry import Point

from salubri_api.config import get_settings
from salubri_api.models import Commune, ImportBatch, Report
from salubri_api.services import data_mode
from salubri_api.services.geo import to_wkb


def _report(c, **kw):  # type: ignore[no-untyped-def]
    return Report(commune_id=c.id, geom=to_wkb(Point(-1.52, 12.37)), status="verified", **kw)


def test_reel_garde_go_et_sdgd(db, monkeypatch):  # type: ignore[no-untyped-def]
    s = db
    c = s.query(Commune).one()
    b = ImportBatch(filename="reports_demo.geojson", format="geojson", uploaded_by="seed")
    s.add(b)
    s.flush()
    s.add_all([
        _report(c, external_id="demo-001-1", import_batch_id=b.id),
        _report(c, external_id="sdgd2020:sdgd-001"),
        _report(c, client_id="go-telephone-1"),
        _report(c, client_id="x", external_id="demo-7"),
    ])  # fmt: skip
    s.commit()
    monkeypatch.setattr(get_settings(), "data_mode", "reel")
    out = data_mode.apply(s, recompute=False)
    assert out["testville"] == 2
    left = {(r.external_id, r.client_id) for r in s.query(Report).all()}
    assert left == {("sdgd2020:sdgd-001", None), (None, "go-telephone-1")}
    assert s.get(ImportBatch, b.id).rolled_back is True
    assert "testville" not in data_mode.apply(s, recompute=False)  # deuxième passage : rien à faire


def test_retour_demo_seulement_apres_reel(db, monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(get_settings(), "data_mode", "demo")
    assert data_mode.apply(db, recompute=False) == {"mode": "demo"}  # jamais retirés : rien à recharger
