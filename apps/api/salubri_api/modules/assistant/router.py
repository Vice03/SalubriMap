# SPDX-License-Identifier: AGPL-3.0-or-later
"""Routes du module « Assistant » sous /api/assistant (montées seulement si SALUBRI_ASSISTANT_ENABLED=true)."""

import json
import queue
import threading
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from salubri_api.modules.assistant import llm, retrieval, service
from salubri_api.modules.assistant.interface import get_session, require_moderateur, settings


def _build_index() -> None:
    from salubri_api.db import get_sessionmaker

    try:
        with get_sessionmaker()() as s:
            retrieval.build_index(s)
    except Exception:  # base pas encore migrée : l'index se construira à la prochaine question
        import logging

        logging.getLogger("salubri.assistant").exception("index des documents non construit")


router = APIRouter(prefix="/assistant", tags=["Assistant (module)"], on_startup=[_build_index])


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=service.MAX_QUESTION_CHARS)


@router.get("/status", summary="Modèle local joignable ? (sans appeler le modèle)")
def status() -> dict[str, Any]:
    st = settings()
    if st.llm_url.startswith("fake:"):
        cli = llm.client()
        return {
            "disponible": not getattr(cli, "down", False),
            "modele": "simulé",
            "adresse": "fake:",
            "modeles": ["simulé"],
        }
    url, model, models = llm.resolve(force=True)
    return {"disponible": bool(models), "modele": model, "adresse": url, "modeles": models[:20]}


@router.post("/ask", summary="Poser une question (modérateurs et administrateurs) ; réponse diffusée en NDJSON")
def ask(body: AskIn, who=Depends(require_moderateur), s: Session = Depends(get_session)) -> StreamingResponse:  # type: ignore[no-untyped-def]
    if who is None:  # POST : require_moderateur a déjà refusé un anonyme ; garde-fou
        raise HTTPException(401, "Connectez-vous")
    if not s.execute(text("SELECT 1 FROM assistant_passages LIMIT 1")).first():
        retrieval.build_index(s)
    try:
        service.rate_check(s, who.label)
    except service.RateLimited as exc:
        raise HTTPException(429, str(exc), headers={"Retry-After": "60"}) from exc
    if settings().llm_url.startswith("fake:"):  # tests : tout dans la requête, comme avant
        ans = service.ask(s, body.question, who.role, who.label, check_rate=False)
        return StreamingResponse(_final(ans, live_tools=False), media_type="application/x-ndjson")

    # Modèle réel : il peut mettre plusieurs minutes sur processeur. Le travail tourne à part ; on renvoie les étapes
    # au fil de l'eau et un signe de vie toutes les 5 s, pour que ni nginx ni le navigateur ne coupent la réponse.
    q: queue.Queue[Any] = queue.Queue()
    role, label, question = who.role, who.label, body.question

    def work() -> None:
        from salubri_api.db import get_sessionmaker

        try:
            with get_sessionmaker()() as s2:
                q.put(("fin", service.ask(s2, question, role, label, emit=lambda e: q.put(("evt", e)),
                                          check_rate=False)))  # fmt: skip
        except Exception as exc:  # jamais d'écran figé : on dit ce qui s'est passé
            import logging

            logging.getLogger("salubri.assistant").exception("assistant")
            q.put(("fin", service.Answer(f"Erreur de l'assistant : {str(exc)[:150]}", available=False)))

    threading.Thread(target=work, daemon=True).start()

    def events() -> Iterator[bytes]:
        while True:
            try:
                kind, val = q.get(timeout=5)
            except queue.Empty:
                yield _line({"type": "attente"})
                continue
            if kind == "evt":
                yield _line(val)
            else:
                yield from _final(val, live_tools=True)
                return

    return StreamingResponse(events(), media_type="application/x-ndjson",
                             headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})  # fmt: skip


def _line(e: dict[str, Any]) -> bytes:
    return (json.dumps(e, ensure_ascii=False) + "\n").encode()


def _final(ans: service.Answer, live_tools: bool) -> Iterator[bytes]:
    if not live_tools:
        for name in ans.tools_used:
            yield _line({"type": "outil", "nom": name})
    words = ans.text.split(" ")
    for i in range(0, len(words), 8):  # réponse envoyée par morceaux (lecture progressive à l'écran)
        yield _line({"type": "texte", "texte": " ".join(words[i : i + 8]) + " "})
    yield _line({"type": "fin", "sources": ans.sources, "proposition": ans.proposal, "disponible": ans.available})
