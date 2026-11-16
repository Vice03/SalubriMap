# SPDX-License-Identifier: AGPL-3.0-or-later
"""Resume work interrupted by a server restart (background tasks live in the API process).

At startup: plan versions left 'running' go back to 'pending' and every scenario with pending versions is
recomputed; simulation runs left unfinished are marked failed with a clear message (they are cheap to relaunch).
"""

import logging

from salubri_api.db import get_sessionmaker
from salubri_api.models import PlanVersion, SimRun, utcnow
from salubri_api.services import background

log = logging.getLogger(__name__)


def resume_interrupted(sync: bool = False) -> list[str]:
    """Return the ids of the scenarios whose pending versions were (re)started."""
    from salubri_api.services.plan.pipeline import run_pending

    with get_sessionmaker()() as s:
        stuck = s.query(PlanVersion).filter(PlanVersion.status == "running").all()
        for pv in stuck:
            pv.status, pv.started_at = "pending", None
        sims = s.query(SimRun).filter(SimRun.status.in_(("pending", "running"))).all()
        for run in sims:
            run.status, run.error = "failed", "Interrompue par un redémarrage du serveur : relancez la simulation."
            if hasattr(run, "finished_at"):
                run.finished_at = utcnow()
        scenario_ids = sorted(
            {str(x) for (x,) in s.query(PlanVersion.scenario_id).filter(PlanVersion.status == "pending").distinct()}
        )
        s.commit()
    if stuck or sims or scenario_ids:
        log.warning(
            "Reprise après redémarrage : %d version(s) relancée(s), %d simulation(s) interrompue(s)",
            len(scenario_ids),
            len(sims),
        )
    for sid in scenario_ids:
        if sync:
            run_pending(sid)
        else:
            background.spawn(run_pending, sid, name=f"resume-{sid}")
    return scenario_ids
