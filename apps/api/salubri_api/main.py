# SPDX-License-Identifier: AGPL-3.0-or-later
"""Salubri API entry point."""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from salubri_api import __version__
from salubri_api.config import get_settings
from salubri_api.routers import (
    audit,
    auth,
    communes,
    dumps,
    export,
    health,
    imports,
    plans,
    quartiers,
    reports,
    scenarios,
    sim,
    validation,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def problem(status: int, title: str, detail: Any, errors: list[Any] | None = None) -> JSONResponse:
    body: dict[str, Any] = {"type": "about:blank", "title": title, "status": status, "detail": detail}
    if errors is not None:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Salubri API",
        version=__version__,
        description="Aide à la décision pour l'assainissement de Ouagadougou : signalements vérifiés, "
        "plan de collecte, simulation multi-agents. Licence AGPL-3.0.",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if origins:
        app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(HTTPException)
    async def http_exc(_: Request, exc: HTTPException) -> JSONResponse:
        titles = {
            404: "Introuvable",
            409: "Conflit",
            413: "Trop volumineux",
            422: "Données invalides",
            503: "Service indisponible",
        }
        return problem(exc.status_code, titles.get(exc.status_code, "Erreur"), exc.detail)

    @app.exception_handler(RequestValidationError)
    async def validation_exc(_: Request, exc: RequestValidationError) -> JSONResponse:
        errs = [{"loc": list(e.get("loc", [])), "msg": e.get("msg")} for e in exc.errors()]
        return problem(422, "Données invalides", "Certains champs sont invalides", errs)

    for r in (
        health,
        auth,
        communes,
        quartiers,
        reports,
        imports,
        dumps,
        scenarios,
        plans,
        sim,
        export,
        audit,
        validation,
    ):
        app.include_router(r.router, prefix="/api")

    @app.on_event("startup")
    def _security() -> None:  # pas de secret par défaut hors mode démonstration (lève InsecureConfig)
        from salubri_api.db import get_sessionmaker
        from salubri_api.services.security_config import check_startup

        with get_sessionmaker()() as s:
            check_startup(settings, s)

    @app.on_event("startup")
    def _resume() -> None:  # plans and simulations interrupted by a restart
        if settings.resume_on_startup:
            from salubri_api.services.plan.recovery import resume_interrupted

            try:
                resume_interrupted()
            except Exception:  # base absente ou pas encore migrée : le seed s'en charge
                logging.getLogger(__name__).exception("reprise au démarrage impossible")

    settings.photos_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/photos", StaticFiles(directory=settings.photos_dir), name="photos")
    return app


app = create_app()
