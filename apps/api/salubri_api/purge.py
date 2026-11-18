# SPDX-License-Identifier: AGPL-3.0-or-later
"""Purge des signalements, en gardant les données de référence.

    python -m salubri_api.purge signalements [--oui]

Supprime, dans UNE transaction : signalements (photos et « route impraticable » avec eux), dépotoirs consolidés
(nettoyages, récidives, alertes Laabal), lots d'import de signalements, états de route créés par des signalements et
entrées du journal qui s'y rapportent ; puis vide le dossier des photos et relance le calcul du plan de chaque
scénario. Communes, quartiers, îlots, bâtiments, routes, eau, points d'intérêt, comptes, flotte, scénarios et
paramètres ne sont pas touchés."""

import argparse
import sys
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from salubri_api.config import get_settings
from salubri_api.db import get_engine, get_sessionmaker

# tables qui doivent exister pour reconnaître une base Salubri
BASE_SALUBRI = (
    "communes",
    "quartiers",
    "reports",
    "dump_sites",
    "scenarios",
    "plan_versions",
    "audit_log",
)
ENTITES_JOURNAL = ("report", "import_batch", "dump_site")


class BaseInconnue(Exception):
    pass


def verifier_base(engine: Engine) -> None:
    """Refuse de tourner si la base n'est pas celle de Salubri."""
    present = set(inspect(engine).get_table_names())
    manque = [t for t in BASE_SALUBRI if t not in present]
    if manque:
        raise BaseInconnue("Cette base n'est pas celle de Salubri (tables absentes : " + ", ".join(manque) + ").")


def _n(s: Session, sql: str) -> int:
    return int(s.execute(text(sql)).scalar_one())


def purger_base(s: Session) -> dict[str, int]:
    """Supprime le groupe « signalements » (sans commit : l'appelant valide la transaction). Renvoie les nombres."""
    tables = set(inspect(s.get_bind()).get_table_names())
    out: dict[str, int] = {}
    journal = "entity in (" + ",".join(f"'{e}'" for e in ENTITES_JOURNAL) + ")"
    if "road_conditions" in tables:
        out["road_conditions (issues de signalements)"] = _n(
            s, "SELECT count(*) FROM road_conditions WHERE source = 'report'"
        )
        s.execute(text("DELETE FROM road_conditions WHERE source = 'report'"))
    if "road_reports" in tables:
        out["road_reports"] = _n(s, "SELECT count(*) FROM road_reports")  # supprimés avec les signalements (cascade)
    out["photos"] = _n(s, "SELECT count(*) FROM photos")  # idem
    out["reports"] = _n(s, "SELECT count(*) FROM reports")
    s.execute(text("DELETE FROM reports"))
    out["dump_sites"] = _n(s, "SELECT count(*) FROM dump_sites")
    s.execute(text("DELETE FROM dump_sites"))
    out["import_batches"] = _n(s, "SELECT count(*) FROM import_batches")
    s.execute(text("DELETE FROM import_batches"))
    out["audit_log (signalements, dépotoirs, imports)"] = _n(s, f"SELECT count(*) FROM audit_log WHERE {journal}")
    s.execute(text(f"DELETE FROM audit_log WHERE {journal}"))
    return out


def vider_photos(dossier: Path) -> int:
    """Vide le dossier des photos (public et « prive/ ») sans le supprimer."""
    n = 0
    if not dossier.is_dir():
        return 0
    for p in sorted(dossier.rglob("*"), key=lambda q: len(q.parts), reverse=True):
        if p.is_file() or p.is_symlink():
            p.unlink()
            n += 1
        elif p.is_dir():
            p.rmdir()
    return n


def recalculer_plans() -> dict[str, str]:
    from salubri_api.models import Scenario
    from salubri_api.services.plan.pipeline import request_recompute, reset_cache

    reset_cache()
    res: dict[str, str] = {}
    with get_sessionmaker()() as s:
        for sc in s.query(Scenario).order_by(Scenario.created_at).all():
            pv = request_recompute(s, sc, "manual", {"reason": "purge des signalements"}, sync=True)
            res[sc.name] = f"v{pv.version} {pv.status}" + (f" ({pv.error})" if pv.error else "")
    return res


def purger_signalements(oui: bool = False) -> int:
    engine = get_engine()
    try:
        verifier_base(engine)
    except BaseInconnue as e:
        print(f"Refusé : {e}")
        return 2
    if not oui:
        print("Ceci supprime TOUS les signalements, photos, dépotoirs, lots d'import et leur journal.")
        print("Les données de référence (quartiers, routes, bâtiments, CCT, comptes, flotte, scénarios) sont gardées.")
        try:
            rep = input("Taper PURGER pour confirmer : ").strip()
        except EOFError:
            rep = ""
        if rep != "PURGER":
            print("Annulé : rien n'a été supprimé.")
            return 1
    with get_sessionmaker()() as s:
        try:
            compte = purger_base(s)
            s.commit()
        except Exception:
            s.rollback()
            raise
    photos = vider_photos(get_settings().photos_dir)
    print("Supprimé :")
    for t, n in compte.items():
        print(f"  {t:<48}{n:>8}")
    print(f"  {'fichiers photo':<48}{photos:>8}")
    print("Recalcul du plan de chaque scénario sur les données de référence…")
    for nom, etat in recalculer_plans().items():
        print(f"  {nom} : {etat}")
    print("Terminé.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m salubri_api.purge", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cible", required=True)
    p = sub.add_parser("signalements", help="supprime les signalements et ce qui en découle")
    p.add_argument("--oui", action="store_true", help="sans demander de confirmation")
    a = ap.parse_args(argv)
    return purger_signalements(a.oui)


if __name__ == "__main__":
    sys.exit(main())
