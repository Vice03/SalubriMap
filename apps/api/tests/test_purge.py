# SPDX-License-Identifier: AGPL-3.0-or-later
"""Purge des signalements : tout ce qui vient des signalements part, la référence reste ; base inconnue refusée."""

import pytest
from shapely.geometry import Point
from sqlalchemy import create_engine, text

from salubri_api import purge
from salubri_api.config import get_settings
from salubri_api.models import AuditLog, Commune, DumpSite, ImportBatch, Quartier, Report, Scenario, Vehicle, utcnow
from salubri_api.services import data_mode
from salubri_api.services.geo import to_wkb


def _report(c, **kw):  # type: ignore[no-untyped-def]
    return Report(commune_id=c.id, geom=to_wkb(Point(-1.52, 12.37)), status="verified", **kw)


def test_purge_garde_la_reference(db):  # type: ignore[no-untyped-def]
    s = db
    c = s.query(Commune).one()
    b = ImportBatch(filename="x.geojson", format="geojson", uploaded_by="seed")
    s.add(b)
    s.flush()
    s.add_all([_report(c, client_id="go-1"), _report(c, external_id="sdgd2020:a", import_batch_id=b.id)])
    s.add(
        DumpSite(
            commune_id=c.id,
            geom=to_wkb(Point(-1.52, 12.37)),
            dominant_type="mixed",
            first_reported_at=utcnow(),
            last_reported_at=utcnow(),
        )  # fmt: skip
    )
    s.add_all([AuditLog(action="moderate", entity="report"), AuditLog(action="create", entity="vehicle")])
    s.commit()
    avant = (s.query(Quartier).count(), s.query(Scenario).count(), s.query(Vehicle).count())

    out = purge.purger_base(s)
    s.commit()

    assert out["reports"] == 2 and out["dump_sites"] == 1 and out["import_batches"] == 1
    assert s.query(Report).count() == s.query(DumpSite).count() == s.query(ImportBatch).count() == 0
    assert [a.entity for a in s.query(AuditLog).all()] == ["vehicle"]  # le reste du journal est gardé
    assert (s.query(Quartier).count(), s.query(Scenario).count(), s.query(Vehicle).count()) == avant


def test_vider_photos_garde_le_dossier(tmp_path):  # type: ignore[no-untyped-def]
    (tmp_path / "prive").mkdir()
    (tmp_path / "a.jpg").write_bytes(b"x")
    (tmp_path / "prive" / "b.jpg").write_bytes(b"x")
    assert purge.vider_photos(tmp_path) == 2
    assert tmp_path.is_dir() and not list(tmp_path.iterdir())


def test_base_inconnue_refusee():
    with pytest.raises(purge.BaseInconnue):
        purge.verifier_base(create_engine("sqlite://"))


def test_confirmation_exigee(monkeypatch, db):  # type: ignore[no-untyped-def]
    monkeypatch.setattr("builtins.input", lambda *_: "non")
    assert purge.purger_signalements() == 1  # rien n'est supprimé sans « PURGER »


def test_mode_reference_retire_aussi_le_sdgd(db, monkeypatch):  # type: ignore[no-untyped-def]
    s = db
    c = s.query(Commune).one()
    s.add_all([_report(c, external_id="sdgd2020:a"), _report(c, client_id="go-1")])
    s.commit()
    monkeypatch.setattr(get_settings(), "data_mode", "reference")
    assert data_mode.apply(s, recompute=False)["testville"] == 1
    assert [r.client_id for r in s.query(Report).all()] == ["go-1"]  # Salubri Go reste
    assert s.execute(text("select count(*) from reports")).scalar_one() == 1
