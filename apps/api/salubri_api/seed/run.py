# SPDX-License-Identifier: AGPL-3.0-or-later
"""Seed: migrations, commune data, OSM/Open Buildings (or the synthetic city), ilots, scenarios, demo reports,
first plans. Idempotent: does nothing if the commune exists, unless --force.

    python -m salubri_api.seed.run [--commune ouagadougou] [--force] [--no-reports] [--no-plans]
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from shapely.geometry import box
from sqlalchemy import text

from salubri_api.config import get_settings
from salubri_api.db import get_sessionmaker
from salubri_api.models import Commune, Scenario
from salubri_api.seed.load_buildings import load_buildings
from salubri_api.seed.load_commune import (
    insert_world,
    load_commune,
    load_quartiers,
    load_vehicles_and_scenarios,
    synthetic_world_for,
)
from salubri_api.seed.load_reference import load_sdgd_dumps
from salubri_api.seed.synthetic import photo_for_name
from salubri_api.services.consolidation import consolidate
from salubri_api.services.ilots import rebuild_ilots
from salubri_api.services.importers.run import run_import

log = logging.getLogger("salubri.seed")
API_DIR = Path(__file__).resolve().parents[2]


def migrate() -> None:
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "alembic"))
    # migrations des modules optionnels (salubri_api/modules/<nom>/migrations), chacune sur sa branche : un
    # module supprimé disparaît de la liste ; « heads » applique toutes les branches (une seule sans module)
    mods = sorted(str(d) for d in (API_DIR / "salubri_api" / "modules").glob("*/migrations") if d.is_dir())
    cfg.set_main_option("version_locations", " ".join([str(API_DIR / "alembic" / "versions"), *mods]))
    command.upgrade(cfg, "heads")


def demo_photos(fc: dict) -> dict[str, bytes]:  # type: ignore[type-arg]
    out: dict[str, bytes] = {}
    for f in fc.get("features", []):
        name = str(f.get("properties", {}).get("photo") or "")
        if name and name not in out:
            data = photo_for_name(name)
            if data is not None:
                out[name] = data
    return out


def seed(slug: str, force: bool = False, reports: bool = True, plans: bool = True) -> dict[str, object]:
    settings = get_settings()
    data = settings.data_dir
    folder = data / "communes" / slug
    t0 = time.perf_counter()
    migrate()
    summary: dict[str, object] = {"commune": slug}
    with get_sessionmaker()() as s:
        existing = s.query(Commune).filter(Commune.slug == slug).first()
        if existing is not None and not force:
            added = load_sdgd_dumps(s, existing) if reports else 0
            if not added:
                log.info("Commune « %s » déjà chargée : rien à faire (--force pour recharger)", slug)
                return {"commune": slug, "skipped": True}
            consolidate(s, existing.id)
            s.commit()
            log.info("SDGD 2020 : %d décharges officielles ajoutées, recalcul des plans", added)
            from salubri_api.services.plan.pipeline import request_recompute

            for sc in s.query(Scenario).filter(Scenario.commune_id == existing.id).all():
                request_recompute(s, sc, "manual", {"reason": "données SDGD 2020"}, sync=True)
            return {"commune": slug, "sdgd_dumps": added}
        if existing is not None:
            s.delete(existing)
            s.commit()
        commune = load_commune(s, folder)
        quartiers = load_quartiers(s, commune, folder)
        meta = json.loads((folder / "commune.json").read_text(encoding="utf-8"))
        qfc = json.loads((folder / "quartiers.geojson").read_text(encoding="utf-8"))
        pbf = data / "osm" / meta.get("osm_extract", "ouaga.osm.pbf")
        blds = data / "open_buildings" / meta.get("buildings", "ouaga_buildings.csv.gz")
        real_osm, real_bld = pbf.exists() and pbf.stat().st_size > 0, blds.exists() and blds.stat().st_size > 0
        if real_osm:
            from salubri_api.seed.load_osm import load_osm  # osmium only needed with a real extract

            summary["osm"] = load_osm(s, commune.id, pbf, box(*meta["bbox"]))
        if real_bld:
            summary["buildings"] = load_buildings(s, commune.id, blds)
        if not (real_osm and real_bld):
            log.warning(
                "Extrait OSM ou Open Buildings absent : ville synthétique pour %s",
                ", ".join(x for x, ok in (("voies/eau", real_osm), ("bâtiments", real_bld)) if not ok),
            )
            world = synthetic_world_for(meta, qfc)
            summary["synthetic"] = insert_world(
                s, commune.id, world, roads=not real_osm, water=not real_osm, buildings=not real_bld
            )
        s.commit()
        n_ilots = sum(rebuild_ilots(s, q) for q in quartiers)
        summary["ilots"] = n_ilots
        scenarios = load_vehicles_and_scenarios(s, commune, folder, quartiers)
        s.commit()

        if reports:
            for fname in ("reports_demo.geojson", "reports_field.geojson"):
                path = folder / fname
                if not path.exists() or path.stat().st_size == 0:
                    continue
                fc = json.loads(path.read_text(encoding="utf-8"))
                res = run_import(s, commune, fname, path.read_bytes(), "geojson", False, "seed", demo_photos(fc))
                summary[fname] = {"accepted": res.accepted, "rejected": res.rejected}
            summary["sdgd_dumps"] = load_sdgd_dumps(s, commune)
            summary["dump_sites"] = consolidate(s, commune.id)
            s.commit()
        counts = {
            t: s.execute(text(f"SELECT count(*) FROM {t}")).scalar_one()
            for t in ("quartiers", "buildings", "water", "roads", "pois", "ilots", "reports", "dump_sites")
        }
        summary["counts"] = counts
        scen_ids = [str(sc.id) for sc in scenarios]

    if plans:
        from salubri_api.services.plan.pipeline import request_recompute

        with get_sessionmaker()() as s:
            for sid in scen_ids:
                sc = s.get(Scenario, __import__("uuid").UUID(sid))
                pv = request_recompute(s, sc, "manual", {"reason": "seed"}, sync=True)  # type: ignore[arg-type]
                summary[f"plan:{sc.name}"] = {
                    "status": pv.status,
                    "error": pv.error,  # type: ignore[union-attr]
                    "points": pv.summary.get("points"),
                    "routes": pv.summary.get("routes"),
                    "unserved": pv.summary.get("unserved_points"),
                }
    summary["seconds"] = round(time.perf_counter() - t0, 1)
    return summary


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    ap = argparse.ArgumentParser(description="Charge les données de démonstration Salubri")
    ap.add_argument("--commune", default=get_settings().commune)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-reports", action="store_true")
    ap.add_argument("--no-plans", action="store_true")
    a = ap.parse_args()
    out = seed(a.commune, a.force, not a.no_reports, not a.no_plans)
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    sys.exit(0)


if __name__ == "__main__":
    main()
