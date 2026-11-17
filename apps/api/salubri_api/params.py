# SPDX-License-Identifier: AGPL-3.0-or-later
"""Paramètres documentés de la commune : vérification, documentation et import des valeurs de la mairie.

    python -m salubri_api.params check [--commune ouagadougou]
    python -m salubri_api.params doc                       # écrit docs/PARAMETRES.md
    python -m salubri_api.params import mairie.json [--commune ouagadougou] [--simulation] [--ecrire-fichier]

`data/communes/<slug>/params_schema.json` donne pour chaque clé de `params_default.json` (y compris `validation`)
l'unité, l'intervalle plausible, la valeur par défaut, la source et les modèles qui l'utilisent. Une valeur hors de
l'intervalle est refusée au chargement (seed, import), avec un message en français.

`import` lit un JSON partiel (mêmes clés, `validation` comprise), le vérifie, affiche les différences avec les valeurs
en base, puis les enregistre comme valeurs de la commune et, avec `--simulation`, dans le scénario de référence
(qui est recalculé). `--a-blanc` affiche les différences sans rien écrire.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from salubri_api.config import REPO_ROOT, get_settings

META_KEYS = {"_sources", "_description"}


class ParamError(ValueError):
    """Paramètres refusés : la liste des problèmes, en français."""

    def __init__(self, problems: list[str]):
        super().__init__("Paramètres refusés :\n- " + "\n- ".join(problems))
        self.problems = problems


def folder(slug: str = "ouagadougou") -> Path:
    return get_settings().data_dir / "communes" / slug


def load_schema(slug: str = "ouagadougou") -> dict[str, Any]:
    """Schéma de la commune ; à défaut celui de Ouagadougou (mêmes clés pour toute commune, NOUVELLE_COMMUNE.md)."""
    f = folder(slug) / "params_schema.json"
    if not f.exists():
        f = folder("ouagadougou") / "params_schema.json"
    data: dict[str, Any] = json.loads(f.read_text(encoding="utf-8"))
    return data


def _check_one(key: str, value: Any, meta: dict[str, Any] | None) -> str | None:
    if meta is None:
        return f"« {key} » : paramètre inconnu (voir docs/PARAMETRES.md)"
    if "valeurs" in meta:
        return None if value in meta["valeurs"] else f"« {key} » = {value!r} : valeurs possibles {meta['valeurs']}"
    if isinstance(value, bool) or not isinstance(value, int | float):
        return f"« {key} » = {value!r} : un nombre est attendu ({meta['unite']})"
    if not meta["min"] <= value <= meta["max"]:
        return (
            f"« {key} » = {value} {meta['unite']} hors de l'intervalle plausible [{meta['min']} ; {meta['max']}] "
            f"({meta['libelle']})"
        )
    return None


def check(values: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Problèmes d'un jeu de paramètres (complet ou partiel) ; liste vide = accepté."""
    problems = []
    for k, v in values.items():
        if k in META_KEYS:
            continue
        if k == "validation":
            if not isinstance(v, dict):
                problems.append("« validation » doit être un objet")
                continue
            for vk, vv in v.items():
                if (p := _check_one(f"validation.{vk}", vv, schema["validation"].get(vk))) is not None:
                    problems.append(
                        p.replace(f"« validation.{vk} » : paramètre inconnu", f"« validation.{vk} » : seuil inconnu")
                    )
            continue
        if (p := _check_one(k, v, schema["parametres"].get(k))) is not None:
            problems.append(p)
    return problems


def validate(values: dict[str, Any], slug: str = "ouagadougou") -> None:
    if problems := check(values, load_schema(slug)):
        raise ParamError(problems)


def diff(old: dict[str, Any], new: dict[str, Any]) -> list[tuple[str, Any, Any]]:
    out = []
    for k, v in new.items():
        if k in META_KEYS:
            continue
        if k == "validation":
            out += [(f"validation.{vk}", (old.get("validation") or {}).get(vk), vv) for vk, vv in v.items()
                    if (old.get("validation") or {}).get(vk) != vv]  # fmt: skip
        elif old.get(k) != v:
            out.append((k, old.get(k), v))
    return out


def merge(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    out = {**old, **{k: v for k, v in new.items() if k != "validation"}}
    if "validation" in new:
        out["validation"] = {**(old.get("validation") or {}), **new["validation"]}
    return out


def _fmt(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:,.6g}".replace(",", " ").replace(".", ",")
    if isinstance(v, int) and not isinstance(v, bool):
        return f"{v:,}".replace(",", " ")
    return str(v)


def render_doc(schema: dict[str, Any], defaults: dict[str, Any]) -> str:
    lines = [
        "<!-- SPDX-License-Identifier: CC-BY-4.0 -->",
        "# Paramètres",
        "",
        "Généré par `python -m salubri_api.params doc` depuis `data/communes/ouagadougou/params_schema.json` — ne pas "
        "modifier à la main. Les valeurs de départ sont dans `params_default.json` ; chaque scénario les copie et "
        "Salubri Sim permet de les changer. Une valeur hors de l'intervalle plausible est refusée au chargement.",
        "",
        "**Charger les valeurs de la mairie** (une commande, avec rapport des différences) :",
        "",
        "```bash",
        "docker compose exec api python -m salubri_api.params import /chemin/mairie.json --simulation",
        "```",
        "",
        "Le fichier ne contient que les clés à changer, par exemple "
        '`{"budget_fcfa_month": 31000000, "waste_kg_per_person_day": 0.55, "validation": {"duplicate_radius_m": 25}}`. '
        "`--a-blanc` affiche les différences sans rien écrire.",
        "",
        "Sources : **mairie** (donnée à obtenir ou obtenue), **littérature** (référence citée), **choix technique** "
        "ou **hypothèse** (avec justification, à remplacer dès qu'une donnée existe).",
        "",
    ]
    for title, key, vals in (
        ("Plan et simulation", "parametres", defaults),
        ("Règles de validation des signalements", "validation", defaults.get("validation", {})),
    ):
        lines += [
            f"## {title}",
            "",
            "| Clé | Paramètre | Unité | Intervalle plausible | Défaut | Source | Utilisé par |",
            "|---|---|---|---|---|---|---|",
        ]
        for k, m in schema[key].items():
            rng = " / ".join(m["valeurs"]) if "valeurs" in m else f"{_fmt(m['min'])} – {_fmt(m['max'])}"
            lines.append(
                f"| `{k}` | {m['libelle']} | {m['unite']} | {rng} | {_fmt(vals.get(k, m['defaut']))} | {m['source']} "
                f"| {', '.join(m['modeles'])} |"
            )
        lines.append("")
    lines += [
        "## Paramètres de comportement du modèle à agents",
        "",
        "Propres à la simulation, hors de ce fichier : `apps/api/salubri_api/services/simulation/abm/params.py`, "
        "décrits et justifiés dans `docs/SIMULATION_ODD.md` § 7 ; leur influence est mesurée dans "
        "`docs/SENSIBILITE.md`.",
        "",
    ]
    return "\n".join(lines)


def _import(path: Path, slug: str, simulation: bool, dry: bool, write_file: bool) -> int:
    from salubri_api.db import get_sessionmaker
    from salubri_api.models import Commune, Scenario
    from salubri_api.services.params import PARAM_EVENT, ScenarioParams, widest_event

    try:
        new = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Fichier illisible : {exc}", file=sys.stderr)
        return 2
    if not isinstance(new, dict):
        print("Le fichier doit contenir un objet JSON { clé: valeur }", file=sys.stderr)
        return 2
    if problems := check(new, load_schema(slug)):
        print("Paramètres refusés :\n- " + "\n- ".join(problems), file=sys.stderr)
        return 1
    with get_sessionmaker()() as s:
        commune = s.query(Commune).filter(Commune.slug == slug).one_or_none()
        if commune is None:
            print(f"Commune « {slug} » absente de la base : lancer le seed", file=sys.stderr)
            return 2
        changes = diff(commune.params_default or {}, new)
        print(f"{len(changes)} changement(s) pour {commune.name} :")
        for k, a, b in changes:
            print(f"  {k:36} {_fmt(a):>16} → {_fmt(b)}")
        if dry or not changes:
            print("À blanc : rien n'est écrit." if dry else "Rien à changer.")
            return 0
        commune.params_default = merge(commune.params_default or {}, new)
        if simulation:
            base = (
                s.query(Scenario)
                .filter(Scenario.commune_id == commune.id, Scenario.is_baseline.is_(True))
                .one_or_none()
            )
            if base is not None:
                cur = ScenarioParams(**(base.params or {}))
                upd = {k: v for k, v in new.items() if k not in META_KEYS and k != "validation"}
                base.params = ScenarioParams(**{**cur.model_dump(), **upd}).model_dump(mode="json")
                s.commit()
                if upd:
                    from salubri_api.services.plan.pipeline import request_recompute

                    kind = widest_event({PARAM_EVENT.get(k, "manual") for k in upd})
                    pv = request_recompute(s, base, kind, {"changed": sorted(upd), "source": "params import"})
                    print(f"Scénario « {base.name} » mis à jour, recalcul demandé (version {pv.version}, {kind}).")
        s.commit()
    if write_file:
        f = folder(slug) / "params_default.json"
        cur = json.loads(f.read_text(encoding="utf-8"))
        f.write_text(json.dumps(merge(cur, new), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{f} mis à jour.")
    print("Valeurs de la commune enregistrées.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m salubri_api.params", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="vérifier params_default.json")
    c.add_argument("--commune", default="ouagadougou")
    sub.add_parser("doc", help="écrire docs/PARAMETRES.md")
    i = sub.add_parser("import", help="charger les valeurs de la mairie")
    i.add_argument("fichier", type=Path)
    i.add_argument("--commune", default="ouagadougou")
    i.add_argument("--simulation", action="store_true", help="appliquer aussi au scénario de référence")
    i.add_argument("--a-blanc", action="store_true", help="afficher les différences sans rien écrire")
    i.add_argument("--ecrire-fichier", action="store_true", help="mettre aussi à jour params_default.json")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        values = json.loads((folder(a.commune) / "params_default.json").read_text(encoding="utf-8"))
        problems = check(values, load_schema(a.commune))
        schema = load_schema(a.commune)
        missing = [k for k in values if k not in META_KEYS and k != "validation" and k not in schema["parametres"]]
        missing += [k for k in values.get("validation", {}) if k not in schema["validation"]]
        for p in problems:
            print(p)
        print("OK" if not problems and not missing else f"{len(problems)} problème(s)")
        return 1 if problems or missing else 0
    if a.cmd == "doc":
        values = json.loads((folder() / "params_default.json").read_text(encoding="utf-8"))
        out = REPO_ROOT / "docs" / "PARAMETRES.md"
        out.write_text(render_doc(load_schema(), values), encoding="utf-8")
        print(f"{out} écrit.")
        return 0
    return _import(a.fichier, a.commune, a.simulation, a.a_blanc, a.ecrire_fichier)


if __name__ == "__main__":
    sys.exit(main())
