# SPDX-License-Identifier: AGPL-3.0-or-later
"""Debounced 'reports_changed' recompute: a burst of reports triggers one recompute per scenario."""

import logging
import threading
import uuid

from salubri_api.config import get_settings
from salubri_api.db import get_sessionmaker
from salubri_api.models import Scenario

log = logging.getLogger("salubri.trigger")
_timers: dict[str, threading.Timer] = {}
_guard = threading.Lock()


def _fire(commune_id: str) -> None:
    from salubri_api.services.plan.pipeline import request_recompute

    with _guard:
        _timers.pop(commune_id, None)
    with get_sessionmaker()() as s:
        for sc in s.query(Scenario).filter(Scenario.commune_id == uuid.UUID(commune_id)).all():
            try:
                request_recompute(s, sc, "reports_changed", {})
            except Exception:
                log.exception("recompute request failed")


def cancel_all() -> None:
    """Annule les recalculs différés en attente (tests, arrêt)."""
    with _guard:
        for t in _timers.values():
            t.cancel()
        _timers.clear()


def reports_changed(commune_id: uuid.UUID) -> None:
    settings = get_settings()
    if not settings.auto_recompute:
        return
    key = str(commune_id)
    with _guard:
        old = _timers.pop(key, None)
        if old:
            old.cancel()
        t = threading.Timer(settings.reports_debounce_s, _fire, args=(key,))
        t.daemon = True
        _timers[key] = t
        t.start()
