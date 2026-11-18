# SPDX-License-Identifier: AGPL-3.0-or-later
"""Chaque outil de lecture sur la petite commune de test, et le client compatible OpenAI sur un faux serveur."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from salubri_api.models import Scenario
from salubri_api.modules.assistant import llm, tools
from salubri_api.services.plan.pipeline import request_recompute


def test_every_read_tool_answers(db, world, client) -> None:  # type: ignore[no-untyped-def]
    from salubri_tests_conftest import free_point, jpeg, post_report

    request_recompute(db, db.query(Scenario).first(), "manual", sync=True)
    request_recompute(db, db.query(Scenario).first(), "fleet_changed", sync=True)
    rep = post_report(client, free_point(world), jpeg(9))
    plan = tools.run(db, "moderateur", "resume_plan", {})
    assert plan["points"] > 0 and plan["scenario"] == "Base"
    pt = tools.run(db, "moderateur", "detail_point", {"point": "P001"})
    assert pt["point"] == "P001" and pt["remplissage_par_enlevement"] >= 0
    assert "erreur" in tools.run(db, "moderateur", "detail_point", {"point": "P999"})
    assert tools.run(db, "moderateur", "diff_versions", {})["evenement"] == "fleet_changed"
    s = tools.run(db, "admin", "signalement", {"report_id": rep["id"]})
    assert s["id"] == rep["id"] and "regles" in s
    assert "erreur" in tools.run(db, "admin", "signalement", {"report_id": "pas-un-uuid"})
    assert tools.run(db, "moderateur", "depotoirs_quartier", {"quartier": "Q1"})["quartier"] == "Q1"
    assert "erreur" in tools.run(db, "moderateur", "depotoirs_quartier", {"quartier": "nulle part"})
    p = tools.run(db, "moderateur", "parametres", {"nom": "walk"})
    assert any(x["cle"] == "walk_distance_max_m" for x in p["parametres"])
    sim = tools.run(db, "moderateur", "resultats_simulation", {})
    assert sim["indicateurs"] and sim["sensibilite_depots_sauvages"]
    pl = tools.run(db, "moderateur", "plan_arrondissement", {"numero": 9, "section": "flotte"})
    assert pl["document"] == "PLAN_ARRONDISSEMENT_9.md" and pl["sections"]
    assert "erreur" in tools.run(db, "moderateur", "plan_arrondissement", {"numero": 99})
    assert "info" in tools.points_saison(db)
    cmp = tools.run(db, "moderateur", "comparer_scenarios", {"scenarios": ["Base"]})
    assert cmp["reference"] == "Base" and cmp["scenarios"][0]["plan_pret"] and cmp["scenarios"][0]["points"] > 0
    assert tools.run(db, "moderateur", "comparer_scenarios", {})["scenarios"]
    eg = tools.run(db, "admin", "etat_general", {})
    assert eg["signalements"] and eg["plan"]["points"] > 0 and "erreur" not in eg
    assert tools.run(db, "moderateur", "outil_inconnu", {})["erreur"].startswith("outil")
    assert tools.run(db, "visiteur", "resume_plan", {})["erreur"].startswith("outil")


def test_openai_compatible_client_and_unavailability() -> None:
    seen = {}

    class H(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            seen["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen["auth"] = self.headers.get("Authorization")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"choices": [{"message": {"role": "assistant", "content": "ok"}}]}).encode())

        def do_GET(self) -> None:  # noqa: N802
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"data": [{"id": "qwen2.5:7b-instruct"}]}).encode())

        def log_message(self, *a: object) -> None:
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        c = llm.OpenAICompatible(f"http://127.0.0.1:{srv.server_address[1]}/v1", "m", "k", 5)
        assert c.chat([{"role": "user", "content": "x"}], [{"type": "function"}])["content"] == "ok"
        assert seen["body"]["model"] == "m" and seen["body"]["tools"] and seen["auth"] == "Bearer k"
        assert c.ping() == ["qwen2.5:7b-instruct"]
    finally:
        srv.shutdown()
    dead = llm.OpenAICompatible("http://127.0.0.1:9/v1", "m", "", 0.5)
    for f in (lambda: dead.chat([], []), dead.ping):
        try:
            f()
            raise AssertionError("aurait dû échouer")
        except llm.Unavailable:
            pass


def test_pick_prefers_wanted_then_biggest_tool_family() -> None:
    installed = ["nomic-embed-text:latest", "llama3.2:3b", "qwen2.5:14b"]
    assert llm.pick(installed, "qwen2.5:7b-instruct") == "qwen2.5:14b"  # le 7B demandé n'est pas installé
    assert llm.pick(installed, "llama3.2:3b") == "llama3.2:3b"
    assert llm.pick(["gemma2:9b", "nomic-embed-text"]) == "gemma2:9b"  # rien d'autre : on prend ce qui est là
    assert llm.pick(["nomic-embed-text"]) is None


def test_resolve_finds_ollama_elsewhere(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from salubri_api.config import get_settings

    class H(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"data": [{"id": "nomic-embed-text"}, {"id": "qwen2.5:14b"}]}).encode())

        def log_message(self, *a: object) -> None:
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        here = f"http://127.0.0.1:{srv.server_address[1]}/v1"
        monkeypatch.setattr(get_settings(), "llm_url", "http://127.0.0.1:9/v1")  # adresse réglée : rien n'y répond
        monkeypatch.setattr(llm, "CANDIDATES", (here,))
        assert llm.resolve(force=True)[:2] == (here, "qwen2.5:14b")
        monkeypatch.setattr(get_settings(), "llm_auto", False)
        assert llm.resolve(force=True)[2] == []  # sans recherche automatique : seulement l'adresse réglée
    finally:
        srv.shutdown()
        llm._found.update(t=-1e9, val=None)
