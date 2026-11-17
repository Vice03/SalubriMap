# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lot C : « 2 camions en panne » juste après un import réutilise E1–E4, 20 fois de suite.

La répétition avait montré une fois un recalcul complet. Cause : elle attendait 3 s fixes après l'import ; si le
recalcul différé « signalements modifiés » (reports_debounce_s) n'était pas fini, le plan de la panne intégrait
l'import et recalculait E1–E4 à juste titre. Correctif : /api/health expose la file de recalculs et
scripts/rehearse.py attend qu'elle soit vide. Ce test vérifie le comportement du serveur dans les deux cas.
"""

import io
import json
import time
import zipfile

from conftest import free_point

from salubri_api.config import get_settings
from salubri_api.models import PlanVersion, Scenario, Vehicle
from salubri_api.services import background
from salubri_api.services.plan import trigger
from salubri_api.services.plan.pipeline import request_recompute


def _import(client, world, n0: int) -> None:  # type: ignore[no-untyped-def]
    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": list(free_point(world, n=n0 + i))},
                "properties": {"device_id": f"jury-{n0 + i}", "type": "menager"},
            }
            for i in range(6)
        ],
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("jury.geojson", json.dumps(fc))
    r = client.post("/api/imports", files={"file": ("jury.zip", buf.getvalue(), "application/zip")})
    assert r.status_code == 200, r.text


def _ran(pv: PlanVersion) -> set[str]:
    return {s["stage"] for s in pv.stages if not s["cache_hit"]}


def test_breakdown_right_after_import_reuses_points_20_times(db, client, world, monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(get_settings(), "auto_recompute", True)
    monkeypatch.setattr(get_settings(), "reports_debounce_s", 0.3)
    sc = db.query(Scenario).first()
    assert request_recompute(db, sc, "manual", sync=True).status == "ready"
    _import(client, world, 100)  # arme le recalcul différé « signalements modifiés »
    assert trigger.pending(sc.commune_id) == 1
    assert client.get("/api/health").json()["queue"]["debounced"] == 1
    # une demande qui arrive pendant l'attente intègre déjà l'import : E1–E4 recalculés, normal
    early = request_recompute(db, sc, "manual", sync=True)
    assert early.status == "ready" and "E1" in _ran(early)
    # puis le recalcul différé part ; E1 (consolidation) est toujours rejoué pour cet événement, par conception,
    # mais il ne trouve rien de neuf : îlots, points et matrice (E2–E4) viennent du cache
    for _ in range(50):
        if not trigger.pending():
            break
        time.sleep(0.1)
    background.drain(60)
    db.expire_all()
    late = db.query(PlanVersion).filter(PlanVersion.scenario_id == sc.id).order_by(PlanVersion.version.desc()).first()
    assert late.event_kind == "reports_changed" and late.status == "ready"
    assert not _ran(late) & {"E2", "E3", "E4"}, _ran(late)
    health = client.get("/api/health").json()
    assert health["queue"] == {"debounced": 0, "pending": 0, "running": 0}
    # 20 pannes « 2 camions » successives : E1–E4 toujours réutilisés
    trucks = db.query(Vehicle).filter(Vehicle.scenario_id == sc.id).order_by(Vehicle.label).limit(2).all()
    seen = []
    for i in range(20):
        for v in trucks:
            v.out_of_service = i % 2 == 0
        db.commit()
        pv = request_recompute(db, sc, "fleet_changed", sync=True)
        assert pv.status == "ready", pv.error
        seen.append(_ran(pv))
    assert all(r == {"E5", "E6", "E7"} for r in seen), seen
