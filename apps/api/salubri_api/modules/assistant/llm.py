# SPDX-License-Identifier: AGPL-3.0-or-later
"""Client de chat compatible OpenAI (`POST {url}/chat/completions` avec `tools`), que proposent Ollama, LM Studio,
llama.cpp server, Jan, LocalAI et vLLM : un seul chemin, pas de chemin propre à Ollama (rien ne manque à l'API
compatible pour cet usage). `SALUBRI_LLM_URL=fake:` branche un modèle simulé pour les tests (CI sans modèle)."""

import json
import re
import time
from collections.abc import Callable
from typing import Any

import httpx

from salubri_api.modules.assistant.interface import settings


class Unavailable(Exception):
    """Serveur de modèle injoignable, en erreur ou trop lent : l'assistant répond « indisponible »."""


Message = dict[str, Any]


class FakeLLM:
    """Modèle simulé : `script` est une liste de réponses (dict message) ou une fonction (messages, outils) → message.
    Enregistre les échanges reçus (`seen`) pour les tests."""

    def __init__(self) -> None:
        self.script: list[Message] | Callable[[list[Message], list[dict[str, Any]]], Message] = []
        self.seen: list[list[Message]] = []
        self.down = False

    def chat(self, messages: list[Message], tools: list[dict[str, Any]]) -> Message:
        if self.down:
            raise Unavailable("modèle simulé arrêté")
        self.seen.append(json.loads(json.dumps(messages)))
        if callable(self.script):
            return self.script(messages, tools)
        if not self.script:
            return {"role": "assistant", "content": "Je ne sais pas."}
        return self.script.pop(0)


FAKE = FakeLLM()


class OpenAICompatible:
    def __init__(self, url: str, model: str, key: str, timeout: float, max_tokens: int = 700) -> None:
        self.url, self.model, self.key, self.timeout, self.max_tokens = url.rstrip("/"), model, key, timeout, max_tokens

    def chat(self, messages: list[Message], tools: list[dict[str, Any]]) -> Message:
        body: dict[str, Any] = {"model": self.model, "messages": messages, "temperature": 0.1,
                                "max_tokens": self.max_tokens, "stream": False}  # fmt: skip
        if tools:
            body["tools"] = tools
        headers = {"Authorization": f"Bearer {self.key}"} if self.key else {}
        try:
            r = httpx.post(f"{self.url}/chat/completions", json=body, headers=headers, timeout=self.timeout)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]  # type: ignore[no-any-return]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise Unavailable(str(exc)[:200]) from exc

    def ping(self) -> list[str]:
        try:
            r = httpx.get(f"{self.url}/models", timeout=2)
            r.raise_for_status()
            return [m.get("id", "") for m in r.json().get("data", [])]
        except (httpx.HTTPError, ValueError) as exc:
            raise Unavailable(str(exc)[:200]) from exc


# Où chercher un modèle déjà lancé sur la machine, vu depuis le conteneur de l'API (puis hors Docker).
CANDIDATES = (
    "http://host.docker.internal:11434/v1",  # Ollama sur le PC
    "http://ollama:11434/v1",  # conteneur Ollama (profil « assistant »)
    "http://localhost:11434/v1",
    "http://host.docker.internal:1234/v1",  # LM Studio
    "http://localhost:1234/v1",
)
FAMILIES = ("qwen3", "qwen2.5", "qwen2_5", "llama3", "llama-3", "mistral")
_found: dict[str, Any] = {"t": -1e9, "val": None}


def _size_b(name: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)\s*b\b", name.lower().replace("_", "."))
    return float(m.group(1)) if m else 7.0


def pick(models: list[str], wanted: str = "") -> str | None:
    """Le modèle demandé s'il est installé ; sinon le plus gros d'une famille qui sait appeler des outils ;
    sinon n'importe quel modèle de texte installé (l'utilisateur l'a choisi)."""
    if wanted and wanted in models:
        return wanted
    text_models = [m for m in models if not any(x in m.lower() for x in ("embed", "vision", "coder", "whisper"))]
    good = [m for m in text_models if any(f in m.lower() for f in FAMILIES)]
    pool = good or text_models
    return sorted(pool, key=lambda m: (_size_b(m), "instruct" in m.lower(), m))[-1] if pool else None


def resolve(force: bool = False) -> tuple[str, str, list[str]]:
    """(adresse, modèle, modèles vus) : l'adresse réglée si elle répond, sinon la première adresse connue où un
    modèle tourne. Résultat gardé 60 s (15 s quand rien ne répond) pour ne pas sonder à chaque question."""
    st = settings()
    now = time.monotonic()
    ttl = 60 if _found["val"] and _found["val"][2] else 15
    if not force and _found["val"] and now - _found["t"] < ttl:
        return _found["val"]  # type: ignore[no-any-return]
    val: tuple[str, str, list[str]] = (st.llm_url, st.llm_model, [])
    for url in dict.fromkeys([st.llm_url, *(CANDIDATES if st.llm_auto else ())]):
        try:
            models = OpenAICompatible(url, st.llm_model, st.llm_api_key, 2).ping()
        except Unavailable:
            continue
        m = pick(models, st.llm_model)
        if m:
            val = (url, m, models)
            break
    _found.update(t=now, val=val)
    return val


def client() -> Any:
    st = settings()
    if st.llm_url.startswith("fake:"):
        return FAKE
    url, model, _ = resolve()
    return OpenAICompatible(url, model, st.llm_api_key, st.llm_timeout_s)
