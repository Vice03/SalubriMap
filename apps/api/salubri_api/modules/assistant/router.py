# SPDX-License-Identifier: AGPL-3.0-or-later
"""Routes du module « Assistant » sous /api/assistant (montées seulement si SALUBRI_ASSISTANT_ENABLED=true)."""

import json
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
    cli = llm.client()
    try:
        models = cli.ping() if hasattr(cli, "ping") else ["simulé"]
        ok = True
    except llm.Unavailable:
        models, ok = [], False
    return {"disponible": ok and not getattr(cli, "down", False), "modele": st.llm_model, "modeles": models[:20]}


@router.post("/ask", summary="Poser une question (modérateurs et administrateurs) ; réponse diffusée en NDJSON")
def ask(body: AskIn, who=Depends(require_moderateur), s: Session = Depends(get_session)) -> StreamingResponse:  # type: ignore[no-untyped-def]
    if who is None:  # POST : require_moderateur a déjà refusé un anonyme ; garde-fou
        raise HTTPException(401, "Connectez-vous")
    if not s.execute(text("SELECT 1 FROM assistant_passages LIMIT 1")).first():
        retrieval.build_index(s)
    try:
        ans = service.ask(s, body.question, who.role, who.label)
    except service.RateLimited as exc:
        raise HTTPException(429, str(exc), headers={"Retry-After": "60"}) from exc

    def events() -> Iterator[bytes]:
        for name in ans.tools_used:
            yield (json.dumps({"type": "outil", "nom": name}, ensure_ascii=False) + "\n").encode()
        words = ans.text.split(" ")
        for i in range(0, len(words), 8):  # réponse envoyée par morceaux (lecture progressive à l'écran)
            yield (json.dumps({"type": "texte", "texte": " ".join(words[i : i + 8]) + " "}, ensure_ascii=False)
                   + "\n").encode()  # fmt: skip
        yield (json.dumps({"type": "fin", "sources": ans.sources, "proposition": ans.proposal,
                           "disponible": ans.available}, ensure_ascii=False) + "\n").encode()  # fmt: skip

    return StreamingResponse(events(), media_type="application/x-ndjson")
