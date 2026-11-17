# SPDX-License-Identifier: AGPL-3.0-or-later
"""Client de chat compatible OpenAI (`POST {url}/chat/completions` avec `tools`), que proposent Ollama, LM Studio,
llama.cpp server, Jan, LocalAI et vLLM : un seul chemin, pas de chemin propre à Ollama (rien ne manque à l'API
compatible pour cet usage). `SALUBRI_LLM_URL=fake:` branche un modèle simulé pour les tests (CI sans modèle)."""

import json
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


def client() -> Any:
    st = settings()
    if st.llm_url.startswith("fake:"):
        return FAKE
    return OpenAICompatible(st.llm_url, st.llm_model, st.llm_api_key, st.llm_timeout_s)
