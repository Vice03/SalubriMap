# SPDX-License-Identifier: AGPL-3.0-or-later
"""run/llm_detect.py (B7) : détection sur de faux serveurs locaux, palier selon la machine, accord avant tout
téléchargement, « ni modèle ni disque » → Salubri démarre sans l'assistant, appel depuis start.bat et start.sh."""

import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[6]
spec = importlib.util.spec_from_file_location("llm_detect", ROOT / "run" / "llm_detect.py")
assert spec and spec.loader
det = importlib.util.module_from_spec(spec)
spec.loader.exec_module(det)


def serve(routes: dict[str, object]) -> tuple[HTTPServer, int]:
    class H(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            body = routes.get(self.path)
            self.send_response(200 if body is not None else 404)
            self.end_headers()
            if body is not None:
                self.wfile.write(json.dumps(body).encode())

        def log_message(self, *a: object) -> None:
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def test_detects_each_runtime_shape_and_skips_salubri(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    ollama, p1 = serve({"/api/tags": {"models": [{"name": "qwen2.5:7b-instruct"}, {"name": "nomic-embed-text"}]}})
    lmstudio, p2 = serve({"/v1/models": {"data": [{"id": "qwen2.5-14b-instruct"}, {"id": "qwen2.5-coder-32b"}]}})
    salubri, p3 = serve({"/api/health": {"status": "ok", "masking": "ok", "queue": {}},
                         "/v1/models": {"data": [{"id": "qwen2.5-72b-instruct"}]}})  # fmt: skip
    monkeypatch.setattr(det, "RUNTIMES", [("Ollama", p1, "/api/tags"), ("LM Studio", p2, "/v1/models"),
                                          ("vLLM", 8000, "/v1/models")])  # fmt: skip
    monkeypatch.setattr(det, "is_salubri", lambda base: base.endswith(":8000") or base.endswith(f":{p3}"))
    try:
        assert det.detect(15, "http://127.0.0.1") == ("LM Studio", f"http://127.0.0.1:{p2}/v1", "qwen2.5-14b-instruct")
        assert det.detect(8, "http://127.0.0.1") == ("Ollama", f"http://127.0.0.1:{p1}/v1", "qwen2.5:7b-instruct")
        assert det.detect(1, "http://127.0.0.1") is None  # rien d'assez petit pour cette machine
        assert det.list_models(f"http://127.0.0.1:{p3}", "/nope") is None
    finally:
        for s in (ollama, lmstudio, salubri):
            s.shutdown()
    assert det.container_url("http://localhost:1234/v1") == "http://host.docker.internal:1234/v1"


def test_hardware_to_tier() -> None:
    H = det.Hardware  # noqa: N806
    assert det.tier_for(H(4, 2, 0, False, 4, 100)) == "aucun"
    assert det.tier_for(H(12, 6, 0, False, 4, 100)) == "petit"
    assert det.tier_for(H(16, 8, 0, False, 8, 100)) == "moyen"
    assert det.tier_for(H(8, 4, 8, False, 8, 100)) == "moyen"  # GPU de 8 Go
    assert det.tier_for(H(32, 20, 0, True, 10, 100)) == "grand"  # Apple, mémoire unifiée
    assert det.tier_for(H(16, 8, 12, False, 8, 100)) == "grand"
    assert all(t.licence in ("", "Apache-2.0") for t in det.TIERS.values())  # aucune licence non libre proposée


@pytest.mark.parametrize(
    ("mode", "env", "tty", "expected"),
    [
        ("no", {}, True, False),
        ("yes", {"SALUBRI_DEMO_MODE": "false"}, False, True),
        ("auto", {"SALUBRI_DEMO_MODE": "false"}, False, False),  # pas de terminal : jamais
        ("auto", {"SALUBRI_DEMO_MODE": "false"}, True, True),  # demandé à l'utilisateur
        ("yes", {"SALUBRI_DEMO_MODE": "true"}, True, False),  # démonstration : jamais
        ("yes", {"SALUBRI_DEMO_MODE": "true", "SALUBRI_LLM_DURING_DEMO": "on"}, True, True),
        ("yes", {"SALUBRI_DEMO_MODE": "false", "CI": "true"}, True, False),
        ("yes", {"SALUBRI_DEMO_MODE": "false", "SALUBRI_NO_LLM_PULL": "1"}, True, False),
    ],
)
def test_consent(mode, env, tty, expected) -> None:  # type: ignore[no-untyped-def]
    assert det.may_pull(mode, env, tty)[0] is expected


def test_no_model_and_no_disk_starts_without_assistant(monkeypatch, tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(det, "ENV", tmp_path / ".env")
    (tmp_path / ".env").write_text("SALUBRI_ASSISTANT_ENABLED=true\nSALUBRI_DEMO_MODE=false\n", encoding="utf-8")
    for k in ("SALUBRI_LLM_URL", "CI", "SALUBRI_NO_LLM_PULL", "SALUBRI_DEMO_MODE", "SALUBRI_ASSISTANT_ENABLED"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(det, "hardware", lambda: det.Hardware(16, 8, 0, False, 8, 2.0))
    monkeypatch.setattr(det, "detect", lambda *a, **k: None)
    pulled = []
    monkeypatch.setattr(det, "pull", lambda *a: pulled.append(a) or True)
    assert det.main(["--llm=yes"]) == 0
    assert "disque insuffisant" in capsys.readouterr().out and not pulled
    assert "SALUBRI_LLM_URL" not in (tmp_path / ".env").read_text(encoding="utf-8")
    monkeypatch.setattr(det, "hardware", lambda: det.Hardware(16, 8, 0, False, 8, 50.0))
    assert det.main(["--llm=yes"]) == 0 and pulled == [("qwen2.5:7b-instruct", False)]
    assert "SALUBRI_LLM_URL=http://ollama:11434/v1" in (tmp_path / ".env").read_text(encoding="utf-8")


def test_found_model_is_written_and_dry_run_writes_nothing(monkeypatch, tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(det, "ENV", tmp_path / ".env")
    (tmp_path / ".env").write_text("SALUBRI_ASSISTANT_ENABLED=true\n", encoding="utf-8")
    monkeypatch.delenv("SALUBRI_LLM_URL", raising=False)
    monkeypatch.setattr(det, "hardware", lambda: det.Hardware(16, 8, 0, False, 8, 50.0))
    monkeypatch.setattr(det, "detect", lambda *a, **k: ("LM Studio", "http://localhost:1234/v1", "qwen2.5-7b-instruct"))
    assert det.main(["--dry-run"]) == 0
    assert "SALUBRI_LLM_URL" not in (tmp_path / ".env").read_text(encoding="utf-8")
    assert det.main([]) == 0
    out = capsys.readouterr().out
    assert "Assistant : modèle qwen2.5-7b-instruct trouvé sur LM Studio" in out
    assert "SALUBRI_LLM_URL=http://host.docker.internal:1234/v1" in (tmp_path / ".env").read_text(encoding="utf-8")


def test_start_scripts_call_detection_only_when_enabled() -> None:
    bat = (ROOT / "run" / "start.bat").read_text(encoding="utf-8")
    sh = (ROOT / "run" / "start.sh").read_text(encoding="utf-8")
    assert 'findstr /b /r /c:"SALUBRI_ASSISTANT_ENABLED=true" .env' in bat and "python run\\llm_detect.py %*" in bat
    assert "SALUBRI_ASSISTANT_ENABLED=(true|1)" in sh and 'python3 run/llm_detect.py "$@"' in sh
    assert "--profile assistant" in bat and "--profile assistant" in sh
