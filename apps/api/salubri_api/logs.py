# SPDX-License-Identifier: AGPL-3.0-or-later
"""Journaux structurés (lot F) : une ligne JSON par évènement, avec l'identifiant de la requête.

SALUBRI_LOG_FORMAT=text garde l'ancien format lisible (développement).
"""

import json
import logging
import os
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id: ContextVar[str] = ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out = {
            "t": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "niveau": record.levelname,
            "source": record.name,
            "message": record.getMessage(),
            "requete": request_id.get(),
        }
        for k in ("methode", "chemin", "statut", "duree_ms"):
            if hasattr(record, k):
                out[k] = getattr(record, k)
        if record.exc_info:
            out["erreur"] = self.formatException(record.exc_info)
        return json.dumps(out, ensure_ascii=False)


def setup_logging() -> None:
    handler = logging.StreamHandler()
    if os.environ.get("SALUBRI_LOG_FORMAT", "json").lower() == "text":
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    else:
        handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").disabled = True  # remplacé par la ligne « requête » ci-dessous


class RequestIdMiddleware(BaseHTTPMiddleware):
    """X-Request-ID repris du client (nginx) ou créé ; renvoyé dans la réponse et présent dans chaque ligne."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        rid = (request.headers.get("x-request-id") or uuid.uuid4().hex[:16])[:64]
        token = request_id.set(rid)
        t0 = time.perf_counter()
        try:
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            if request.url.path != "/api/health":
                logging.getLogger("salubri.requete").info(
                    "%s %s %s",
                    request.method,
                    request.url.path,
                    response.status_code,
                    extra={
                        "methode": request.method,
                        "chemin": request.url.path,
                        "statut": response.status_code,
                        "duree_ms": round((time.perf_counter() - t0) * 1000, 1),
                    },
                )
        finally:
            request_id.reset(token)
        return response
