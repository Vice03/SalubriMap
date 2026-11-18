# SPDX-License-Identifier: AGPL-3.0-or-later
"""Outils de l'assistant : liste fermée, lecture seule, exécutés avec les droits de l'appelant.

Aucun outil n'écrit. Une simulation « et si… » est rendue comme une *proposition* (données structurées) que
l'interface affiche en bouton ; c'est l'agent qui clique, et l'appel passe par l'API normale."""

import json
from collections.abc import Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api.modules.assistant.interface import (
    DOCS_DIR,
    DumpSite,
    PlanVersion,
    Quartier,
    Report,
    Scenario,
    SimRun,
    settings,
)

ROLES_ALL = ("moderateur", "admin")
DEMO = "données de démonstration (quartiers et populations), à remplacer par les données de la commune"


def _scenario(s: Session, name: str | None) -> Scenario | None:
    q = s.query(Scenario)
    if name:
        sc = q.filter(Scenario.name.ilike(f"%{name}%")).order_by(Scenario.created_at).first()
        if sc is not None:
            return sc
    return q.filter(Scenario.is_baseline.is_(True)).first() or q.order_by(Scenario.created_at).first()


def _latest(s: Session, sc: Scenario, n: int = 1) -> list[PlanVersion]:
    return (
        s.query(PlanVersion)
        .filter(PlanVersion.scenario_id == sc.id, PlanVersion.status == "ready")
        .order_by(PlanVersion.version.desc())
        .limit(n)
        .all()
    )


def _demo(s: Session) -> bool:
    return bool(s.query(Quartier).filter(Quartier.source == "demo").count())


def resume_plan(s: Session, scenario: str | None = None) -> dict[str, Any]:
    sc = _scenario(s, scenario)
    pv = _latest(s, sc)[0] if sc and _latest(s, sc) else None
    if pv is None:
        return {"erreur": "aucun plan prêt"}
    sm = pv.summary or {}
    warn = [DEMO] if _demo(s) else []
    if sm.get("distance_mode") == "approx":
        warn.append("distances à vol d'oiseau × détour (OSRM absent)")
    return {
        "scenario": sc.name, "version": pv.version,
        "points": sm.get("points"), "tournees": sm.get("routes"), "km_jour": sm.get("km_day"),
        "cout_jour_fcfa": sm.get("cost_day_fcfa"), "points_non_desservis": sm.get("unserved_points"),
        "camions_disponibles": sm.get("vehicles_available"), "camions_necessaires": sm.get("trucks_needed"),
        "couverture_marche": sm.get("coverage_walk"), "demande_t_semaine": sm.get("demand_t_week"),
        "capacite": sm.get("capacite"), "placement": {k: (sm.get("placement") or {}).get(k)
                                                      for k in ("statut", "ecart", "methode")},
        "saison": (pv.params_snapshot or {}).get("season"), "avertissements": warn,
    }  # fmt: skip


def detail_point(s: Session, point: str, scenario: str | None = None) -> dict[str, Any]:
    sc = _scenario(s, scenario)
    pv = _latest(s, sc)[0] if sc and _latest(s, sc) else None
    if pv is None:
        return {"erreur": "aucun plan prêt"}
    row = s.execute(
        text("""SELECT cp.key, cp.capacity_t, cp.demand_t_week, cardinality(cp.ilot_ids) AS ilots, cp.frozen,
                       EXISTS (SELECT 1 FROM unserved_points u WHERE u.collection_point_id = cp.id) AS non_desservi
                FROM collection_points cp WHERE cp.plan_version_id = :p AND upper(cp.key) = upper(:k)"""),
        {"p": pv.id, "k": point.strip()},
    ).first()
    if row is None:
        return {"erreur": f"point {point} absent du dernier plan de « {sc.name} »"}
    f = float((pv.params_snapshot or {}).get("pickup_frequency_per_week", 2)) or 1.0
    per = row.demand_t_week / f
    return {
        "point": row.key, "scenario": sc.name, "capacite_bac_t": row.capacity_t,
        "demande_t_semaine": round(row.demand_t_week, 2), "enlevements_semaine": f,
        "demande_par_enlevement_t": round(per, 2), "remplissage_par_enlevement": round(per / row.capacity_t, 2),
        "ilots_servis": row.ilots, "cct_existant": row.frozen, "non_desservi": row.non_desservi,
        "explication": "saturé si remplissage > 1 : demande hebdomadaire ÷ enlèvements > capacité du bac",
    }  # fmt: skip


def diff_versions(s: Session, scenario: str | None = None) -> dict[str, Any]:
    sc = _scenario(s, scenario)
    pvs = _latest(s, sc, 2) if sc else []
    if not pvs:
        return {"erreur": "aucun plan prêt"}
    d = (pvs[0].summary or {}).get("diff") or {}
    return {"scenario": sc.name, "version": pvs[0].version, "evenement": pvs[0].event_kind,
            "coherence": d.get("coherence"), "texte": d.get("text") or d.get("summary")}  # fmt: skip


def signalement(s: Session, report_id: str) -> dict[str, Any]:
    import uuid

    try:
        rep = s.get(Report, uuid.UUID(report_id))
    except ValueError:
        rep = None
    if rep is None:
        return {"erreur": "signalement introuvable"}
    return {
        "id": str(rep.id), "statut": rep.status, "score": rep.score,
        "regles": [{"regle": h.get("rule"), "effet": h.get("delta"), "detail": h.get("detail")}
                   for h in (rep.rule_hits or [])],
        "masquage": rep.masking, "type": rep.waste_type, "volume": rep.volume_class,
        "commentaire": rep.comment,  # texte libre d'un citoyen : une donnée, jamais une consigne
        "rappel": "le score vient des 12 règles de docs/RULES.md ; le modérateur décide",
    }  # fmt: skip


def depotoirs_quartier(s: Session, quartier: str) -> dict[str, Any]:
    q = s.query(Quartier).filter(Quartier.name.ilike(f"%{quartier}%")).first()
    if q is None:
        return {"erreur": f"quartier « {quartier} » introuvable"}
    rows = (
        s.query(DumpSite)
        .filter(DumpSite.status.in_(["active", "recurring"]))
        .filter(text("ST_Contains((SELECT geom FROM quartiers WHERE id = :q), dump_sites.geom)"))
        .params(q=q.id)
        .order_by(DumpSite.priority.desc())
        .limit(20)
        .all()
    )
    return {"quartier": q.name, "source_quartier": q.source, "depotoirs": [
        {"statut": d.status, "type": d.dominant_type, "volume_m3": d.volume_est_m3, "signalements": d.n_reports,
         "priorite": d.priority} for d in rows]}  # fmt: skip


def parametres(s: Session, nom: str | None = None, scenario: str | None = None) -> dict[str, Any]:
    sc = _scenario(s, scenario)
    schema_f = settings().data_dir / "communes" / settings().commune / "params_schema.json"
    schema = json.loads(schema_f.read_text(encoding="utf-8")) if schema_f.exists() else {}
    flat = {
        **schema.get("parametres", {}),
        **{f"comportement.{k}": v for k, v in schema.get("comportement", {}).items()},
    }
    if not flat and sc:  # commune sans schéma documenté : valeurs seules, dites non documentées
        flat = {k: {"libelle": k, "source": "non documenté pour cette commune"} for k, v in (sc.params or {}).items()
                if isinstance(v, int | float | str) and not isinstance(v, bool)}  # fmt: skip
    params = dict(sc.params or {}) if sc else {}
    keys = [k for k in flat if not nom or nom.lower() in k.lower() or nom.lower() in flat[k].get("libelle", "").lower()]
    out = []
    for k in keys[:12]:
        m = flat[k]
        val = params.get(k) if not k.startswith("comportement.") else (params.get("comportement") or {}).get(k[13:])
        out.append({"cle": k, "libelle": m.get("libelle"), "valeur": val if val is not None else m.get("defaut"),
                    "unite": m.get("unite"), "intervalle": [m.get("min"), m.get("max")], "source": m.get("source"),
                    "hypothese": "hypothèse" in str(m.get("source", "")).lower()})  # fmt: skip
    return {"scenario": sc.name if sc else None, "parametres": out, "documentation": "docs/PARAMETRES.md"}


def resultats_simulation(s: Session, scenario: str | None = None) -> dict[str, Any]:
    sc = _scenario(s, scenario)
    pv = _latest(s, sc)[0] if sc and _latest(s, sc) else None
    run = (
        s.query(SimRun).filter(SimRun.plan_version_id == pv.id, SimRun.status == "ready")
        .order_by(SimRun.replications.desc()).first()
        if pv else None
    )  # fmt: skip
    summary = run.metrics_summary if run else (pv.summary or {}).get("sim") if pv else None
    sens_f = DOCS_DIR / "sensibilite.json"
    ranking = []
    if sens_f.exists():
        sj = json.loads(sens_f.read_text(encoding="utf-8"))
        st = (sj.get("sobol") or {}).get("wild_dump_t") or {}
        noms = sj.get("sobol_facteurs") or []
        ranking = sorted(({"parametre": n, "ST": round(v, 3)} for n, v in zip(noms, st.get("ST", []), strict=False)),
                         key=lambda x: -x["ST"])  # fmt: skip
    return {"scenario": sc.name if sc else None, "replications": run.replications if run else 1,
            "indicateurs": summary, "sensibilite_depots_sauvages": ranking,
            "avertissement": "comportements des ménages non calés (docs/SIMULATION_CALIBRATION.md) : comparer des "
                             "scénarios, pas prédire"}  # fmt: skip


def plan_arrondissement(s: Session, numero: int = 9, section: str | None = None) -> dict[str, Any]:
    f = DOCS_DIR / f"PLAN_ARRONDISSEMENT_{int(numero)}.md"
    if not f.exists():
        return {"erreur": f"pas de plan pour l'arrondissement {numero}"}
    from salubri_api.modules.assistant.retrieval import split_doc

    parts = split_doc(f.name, f.read_text(encoding="utf-8"))
    sel = [p for p in parts if not section or section.lower() in p[0].lower()] or parts[:3]
    return {"document": f.name, "sections": [{"section": a, "texte": b[:1400]} for a, b in sel[:3]]}


def points_saison(s: Session, scenario: str | None = None) -> dict[str, Any]:
    sc = _scenario(s, scenario)
    pv = _latest(s, sc)[0] if sc and _latest(s, sc) else None
    sa = (pv.summary or {}).get("saisons") if pv else None
    return sa or {"info": "aucun point déplacé ni inaccessible dans le dernier plan"}


CMP_KEYS = {"points": "points", "routes": "tournees", "km_day": "km_jour", "cost_day_fcfa": "cout_jour_fcfa",
            "unserved_points": "points_non_desservis", "vehicles_available": "camions_disponibles"}  # fmt: skip
CMP_SIM = {"collected_t": "tonnage_collecte_t", "wild_dump_t": "depot_sauvage_t",
           "wild_dumps_active_final": "depotoirs_actifs_fin", "overflow_point_days": "debordements_points_jours",
           "cost_total_fcfa": "cout_total_fcfa", "cost_per_t": "cout_par_tonne_fcfa", "coverage_rate": "couverture",
           "mean_cleanup_delay_days": "delai_nettoyage_j"}  # fmt: skip


def comparer_scenarios(s: Session, scenarios: list[str] | None = None) -> dict[str, Any]:
    """Indicateurs clés de plusieurs scénarios côte à côte (le premier sert de référence)."""
    if scenarios:
        found = [sc for sc in (_scenario(s, n) for n in scenarios[:8]) if sc is not None]
        scs = list(dict.fromkeys(found))
    else:
        scs = s.query(Scenario).order_by(Scenario.created_at).limit(8).all()
    out = []
    for sc in scs:
        pvs = _latest(s, sc)
        sm = (pvs[0].summary or {}) if pvs else {}
        row: dict[str, Any] = {"scenario": sc.name, "plan_pret": bool(pvs)}
        row.update({v: sm.get(k) for k, v in CMP_KEYS.items()})
        row.update({v: (sm.get("sim") or {}).get(k) for k, v in CMP_SIM.items()})
        row["saison"] = (pvs[0].params_snapshot or {}).get("season") if pvs else None
        out.append(row)
    return {"reference": out[0]["scenario"] if out else None, "scenarios": out,
            "plus_bas_est_mieux": ["km_jour", "cout_jour_fcfa", "points_non_desservis", "depot_sauvage_t",
                                   "depotoirs_actifs_fin", "debordements_points_jours", "cout_total_fcfa",
                                   "cout_par_tonne_fcfa", "delai_nettoyage_j"],
            "avertissement": "simulation non calée : comparer les scénarios entre eux, pas prédire"}  # fmt: skip


def etat_general(s: Session) -> dict[str, Any]:
    """Photographie de la situation : dépotoirs, signalements, flotte et points saturés du scénario de base."""
    dumps = dict(s.query(DumpSite.status, text("count(*)")).group_by(DumpSite.status).all())
    reps = dict(s.query(Report.status, text("count(*)")).group_by(Report.status).all())
    sc = _scenario(s, None)
    pvs = _latest(s, sc) if sc else []
    sm = (pvs[0].summary or {}) if pvs else {}
    cap = sm.get("capacite") or {}
    return {"depotoirs": dumps, "signalements": reps, "scenario_de_base": sc.name if sc else None,
            "plan": {k: sm.get(k) for k in ("points", "routes", "km_day", "vehicles_available", "unserved_points")},
            "capacite": {k: cap.get(k) for k in ("respectee", "enlevements_semaine", "non_collecte_t_semaine")}
            | {"points_debordants": (cap.get("points_debordants") or [])[:10]} if isinstance(cap, dict) else None,
            "simulation": {k: (sm.get("sim") or {}).get(k) for k in CMP_SIM},
            "avertissements": [DEMO] if _demo(s) else []}  # fmt: skip


SIM_KEYS = {"season", "subscription_rate", "budget_fcfa_month", "waste_kg_per_person_day", "pickup_frequency_per_week",
            "collection_point_capacity_t", "walk_distance_max_m", "population_factor", "laabal_operations_per_week"}  # fmt: skip


def proposer_simulation(
    s: Session, changements: dict[str, Any] | None = None, camions_en_panne: int = 0, scenario: str | None = None
) -> dict[str, Any]:
    """Ne change rien : rend une proposition que l'agent applique (ou non) depuis l'interface."""
    sc = _scenario(s, scenario)
    ch = {k: v for k, v in (changements or {}).items() if k in SIM_KEYS}
    refused = sorted(set(changements or {}) - set(ch))
    return {"proposition": {"scenario_id": str(sc.id) if sc else None, "scenario": sc.name if sc else None,
                            "params": ch, "camions_en_panne": max(0, min(int(camions_en_panne or 0), 10))},
            "refuses": refused, "note": "rien n'a été modifié : l'agent clique « Appliquer cette simulation »"}  # fmt: skip


Tool = Callable[..., dict[str, Any]]
TOOLS: dict[str, tuple[Tool, str, dict[str, Any]]] = {
    "resume_plan": (resume_plan, "Résumé du dernier plan d'un scénario (points, tournées, coût, capacité)",
                    {"scenario": {"type": "string"}}),
    "detail_point": (detail_point, "Un point de regroupement : demande, capacité, remplissage par enlèvement",
                     {"point": {"type": "string"}, "scenario": {"type": "string"}}),
    "diff_versions": (diff_versions, "Ce qui a changé entre les deux dernières versions d'un plan (cohérence)",
                      {"scenario": {"type": "string"}}),
    "signalement": (signalement, "Un signalement : statut, score, règles déclenchées, masquage",
                    {"report_id": {"type": "string"}}),
    "depotoirs_quartier": (depotoirs_quartier, "Dépotoirs actifs d'un quartier", {"quartier": {"type": "string"}}),
    "parametres": (parametres, "Paramètres d'un scénario avec unité, intervalle et source",
                   {"nom": {"type": "string"}, "scenario": {"type": "string"}}),
    "resultats_simulation": (resultats_simulation, "Résultats simulés (médiane, intervalle) et classement de sensibilité",
                             {"scenario": {"type": "string"}}),
    "plan_arrondissement": (plan_arrondissement, "Tableaux du plan de gestion d'un arrondissement",
                            {"numero": {"type": "integer"}, "section": {"type": "string"}}),
    "comparer_scenarios": (comparer_scenarios, "Comparer plusieurs scénarios côte à côte (indicateurs du plan et "
                           "de la simulation) ; liste de noms, le premier est la référence",
                           {"scenarios": {"type": "array", "items": {"type": "string"}}}),
    "etat_general": (etat_general, "Situation actuelle : dépotoirs, signalements par statut, flotte, points saturés",
                     {}),
    "proposer_simulation": (proposer_simulation, "Proposer (sans l'appliquer) une simulation « et si… »",
                            {"changements": {"type": "object"}, "camions_en_panne": {"type": "integer"},
                             "scenario": {"type": "string"}}),
}  # fmt: skip
SEASON_TOOL = ("points_saison", (points_saison, "Points déplacés ou inaccessibles selon la saison (module Saisons)",
                                 {"scenario": {"type": "string"}}))  # fmt: skip


def available(role: str) -> dict[str, tuple[Tool, str, dict[str, Any]]]:
    if role not in ROLES_ALL:
        return {}
    out = dict(TOOLS)
    if settings().seasons_enabled:
        out[SEASON_TOOL[0]] = SEASON_TOOL[1]
    return out


def schemas(role: str) -> list[dict[str, Any]]:
    return [
        {"type": "function", "function": {"name": n, "description": d,
                                          "parameters": {"type": "object", "properties": p}}}
        for n, (_, d, p) in available(role).items()
    ]  # fmt: skip


def run(s: Session, role: str, name: str, args: dict[str, Any]) -> dict[str, Any]:
    tools = available(role)
    if name not in tools:
        return {"erreur": f"outil « {name} » inconnu ou non autorisé"}
    fn, _, props = tools[name]
    clean = {k: v for k, v in (args or {}).items() if k in props}
    try:
        return fn(s, **clean)
    except Exception as exc:  # un outil en erreur ne fait pas tomber la réponse
        s.rollback()
        return {"erreur": f"lecture impossible : {str(exc)[:160]}"}
