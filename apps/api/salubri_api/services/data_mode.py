# SPDX-License-Identifier: AGPL-3.0-or-later
"""Données de démonstration ou données réelles (SALUBRI_DATA_MODE).

- « demo » : les signalements d'exemple (reports_demo.geojson) sont chargés, pour le jury.
- « reel » : on les retire, avec les signalements d'appareils « demo-… » ; restent les décharges et CCT officiels du
  SDGD 2020 (enquête 2019), les signalements envoyés par Salubri Go et les imports faits par la mairie ; les pièges de
  la répétition (« trap-… », de fausses alertes) partent aussi. Rien de réel
  n'est jamais effacé : passer de « reel » à « demo » recharge seulement les exemples.

Appliqué au démarrage de l'API et à la fin du seed ; idempotent et protégé par un verrou PostgreSQL."""

import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api.config import get_settings
from salubri_api.models import Commune, ImportBatch, Report
from salubri_api.services.consolidation import consolidate

log = logging.getLogger(__name__)
DEMO_FILES = ("reports_demo.geojson",)
TRAP_FILES = ("traps.zip",)  # signalements pièges de la répétition (scripts/rehearse.py) : de fausses alertes
LOCK = 815_2026


def _demo_batches(s: Session) -> list[ImportBatch]:
    return (
        s.query(ImportBatch)
        .filter(
            ImportBatch.filename.in_(DEMO_FILES), ImportBatch.uploaded_by == "seed", ImportBatch.rolled_back.is_(False)
        )
        .all()
    )


def to_reel(s: Session, commune: Commune) -> int:
    n = 0
    traps = s.query(ImportBatch).filter(ImportBatch.filename.in_(TRAP_FILES), ImportBatch.rolled_back.is_(False)).all()
    for b in [*_demo_batches(s), *traps]:
        n += s.query(Report).filter(Report.import_batch_id == b.id).delete(synchronize_session=False)
        b.rolled_back = True
    n += (
        s.query(Report)
        .filter(Report.commune_id == commune.id)
        .filter(Report.device_id.like("demo-%") | Report.external_id.like("demo-%") | Report.external_id.like("trap-%"))
        .delete(synchronize_session=False)
    )
    return n


def to_demo(s: Session, commune: Commune) -> int:
    """Recharge les exemples seulement s'ils ont été retirés par le mode « reel » (le seed s'occupe du premier chargement)."""
    removed = (
        s.query(ImportBatch)
        .filter(
            ImportBatch.filename.in_(DEMO_FILES), ImportBatch.uploaded_by == "seed", ImportBatch.rolled_back.is_(True)
        )
        .count()
    )
    if _demo_batches(s) or not removed:
        return 0
    from salubri_api.seed.run import demo_photos
    from salubri_api.services.importers.run import run_import

    folder = get_settings().data_dir / "communes" / commune.slug
    n = 0
    for fname in DEMO_FILES:
        path = folder / fname
        if not path.exists() or path.stat().st_size == 0:
            continue
        fc = json.loads(path.read_text(encoding="utf-8"))
        n += run_import(s, commune, fname, path.read_bytes(), "geojson", False, "seed", demo_photos(fc)).accepted
    return n


def apply(s: Session, recompute: bool = True) -> dict[str, Any]:
    """Met la base dans le mode réglé. Renvoie ce qui a changé (rien la plupart du temps)."""
    mode = get_settings().data_mode
    if not s.execute(text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": LOCK}).scalar():
        return {"mode": mode, "skipped": "verrou"}
    out: dict[str, Any] = {"mode": mode}
    for commune in s.query(Commune).all():
        n = to_reel(s, commune) if mode == "reel" else to_demo(s, commune)
        if not n:
            continue
        s.flush()
        consolidate(s, commune.id)
        out[commune.slug] = n
        log.info("Données %s : %d signalement(s) %s", mode, n, "retiré(s)" if mode == "reel" else "d'exemple chargé(s)")
        if recompute:
            from salubri_api.models import Scenario
            from salubri_api.services.plan.pipeline import request_recompute

            for sc in s.query(Scenario).filter(Scenario.commune_id == commune.id).all():
                request_recompute(s, sc, "manual", {"reason": f"données {mode}"})
    s.commit()
    return out
