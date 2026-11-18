# SPDX-License-Identifier: AGPL-3.0-or-later
"""Une question → passages (BM25) + boucle d'outils en lecture seule → réponse citée, journalisée.

Sécurité : les sorties d'outils et les passages sont enveloppés dans <donnees> (données, jamais consignes) ; aucun
outil n'écrit ; limite de questions par utilisateur, longueur de réponse et délai bornés ; chaque question, appel
d'outil et réponse va dans le journal existant avec l'utilisateur."""

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api.modules.assistant import llm, retrieval, tools
from salubri_api.modules.assistant.interface import audit

MAX_ROUNDS = 4
MAX_ANSWER_CHARS = 3000
MAX_QUESTION_CHARS = 600
RATE_PER_MINUTE = 6
DEADLINE_S = 600  # au-delà, on répond « trop long » plutôt que de laisser l'écran attendre
SLOW = "Le modèle local a mis trop de temps à répondre. Réessayez (le premier appel charge le modèle en mémoire) ou choisissez un modèle plus petit (choix 12 du lanceur)."
UNAVAILABLE = "Assistant indisponible : aucun modèle local ne répond (voir docs/MODULES.md)."
PROMPT = (Path(__file__).parent / "prompt.md").read_text(encoding="utf-8")


@dataclass
class Answer:
    text: str
    sources: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    proposal: dict[str, Any] | None = None
    available: bool = True


class RateLimited(Exception):
    pass


def wrap(source: str, data: Any) -> str:
    """Donnée d'un outil ou d'un document : balisée, chevrons neutralisés pour qu'elle ne ferme pas la balise."""
    body = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, default=str)
    body = body.replace("<", "‹").replace(">", "›")
    return f'<donnees source="{source}">\n{body}\n</donnees>'


def _rate_check(s: Session, actor: str) -> None:
    since = datetime.now(UTC) - timedelta(minutes=1)
    n = s.execute(
        text("SELECT count(*) FROM audit_log WHERE actor = :a AND action = 'assistant_question' AND at >= :t"),
        {"a": actor[:64], "t": since},
    ).scalar()
    if (n or 0) >= RATE_PER_MINUTE:
        raise RateLimited(f"Au plus {RATE_PER_MINUTE} questions par minute : réessayez dans un instant")


def rate_check(s: Session, actor: str) -> None:
    _rate_check(s, actor)


def ask(s: Session, question: str, role: str, actor: str, emit: Callable[[dict[str, Any]], None] | None = None,
        check_rate: bool = True) -> Answer:  # fmt: skip
    """`emit` reçoit les étapes au fil de l'eau (outil appelé, modèle au travail) pour que l'écran ne reste pas muet."""
    say = emit or (lambda e: None)
    question = question.strip()[:MAX_QUESTION_CHARS]
    if check_rate:
        _rate_check(s, actor)
    audit(s, "assistant_question", "assistant", None, after={"question": question}, actor=actor)
    s.commit()
    hits = retrieval.search(s, question, k=4)
    passages = "\n\n".join(wrap(h.cite, h.text) for h in hits) or "(aucun passage trouvé)"
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": f"Passages des documents :\n{passages}\n\nQuestion : {question}"},
    ]
    cli = llm.client()
    used: list[str] = []
    proposal = None
    start = time.monotonic()
    try:
        for i in range(MAX_ROUNDS):
            if time.monotonic() - start > DEADLINE_S:
                raise llm.Unavailable("délai dépassé")
            say(
                {
                    "type": "etape",
                    "texte": "Le modèle lit les documents…" if i == 0 else "Le modèle analyse les résultats…",
                }
            )
            msg = cli.chat(messages, tools.schemas(role))
            calls = msg.get("tool_calls") or []
            if not calls:
                break
            messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
            for c in calls:
                fn = c.get("function") or {}
                name = fn.get("name", "")
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except ValueError:
                    args = {}
                say({"type": "outil", "nom": name})
                out = tools.run(s, role, name, args if isinstance(args, dict) else {})
                used.append(name)
                if name == "proposer_simulation" and "proposition" in out:
                    proposal = out["proposition"]
                audit(s, "assistant_tool", "assistant", None, after={"outil": name, "arguments": args}, actor=actor)
                messages.append({"role": "tool", "tool_call_id": c.get("id", name), "name": name,
                                 "content": wrap(f"outil:{name}", out)})  # fmt: skip
        else:
            msg = {"content": "Je ne sais pas : trop d'étapes pour cette question."}
    except llm.Unavailable as exc:
        audit(s, "assistant_unavailable", "assistant", None, after={"erreur": str(exc)[:200]}, actor=actor)
        s.commit()
        slow = "timed out" in str(exc).lower() or "timeout" in str(exc).lower() or "délai" in str(exc)
        return Answer(SLOW if slow else UNAVAILABLE, available=False)
    answer = (msg.get("content") or "Je ne sais pas.").strip()[:MAX_ANSWER_CHARS]
    sources = [f"outil: {n}" for n in dict.fromkeys(used)] + [h.cite for h in hits]
    if not re.search(r"\[(outil|[^\]]+\.md)", answer) and "je ne sais pas" not in answer.lower():
        # le modèle n'a pas cité : on ajoute ce qu'il a eu sous les yeux (jamais de réponse sans source)
        answer += "\n\nSources : " + "; ".join(sources[:5] or ["aucune"])
    audit(s, "assistant_answer", "assistant", None,
          after={"reponse": answer[:1500], "outils": used, "sources": sources[:8]}, actor=actor)  # fmt: skip
    s.commit()
    return Answer(answer, sources, used, proposal)
