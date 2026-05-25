"""Entry point: construye la FastAPI app + uvicorn runner."""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from sica_api import __version__
from sica_api.routes import extract as extract_routes
from sica_api.routes import health as health_routes
from sica_api.routes import models as models_routes
from sica_api.routes import providers as providers_routes
from sica_api.settings import get_settings


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Asigna un X-Request-ID por request y lo propaga a logs/handlers."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def create_app() -> FastAPI:
    """Factory para la FastAPI app — útil para testing y para uvicorn."""
    settings = get_settings()

    logging.basicConfig(
        level=settings.log_level,
        format='{"level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
    )

    app = FastAPI(
        title="SICA API",
        description=(
            "Backend HTTP de SICA — capa de inteligencia clínica asistiva "
            "materno-infantil. El output es asistivo y requiere confirmación "
            "médica explícita antes de uso clínico."
        ),
        version=__version__,
    )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_origin_regex=settings.allowed_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Error-ID"],
    )

    app.include_router(health_routes.router)
    app.include_router(models_routes.router)
    app.include_router(providers_routes.router)
    app.include_router(extract_routes.router)

    @app.exception_handler(Exception)
    async def _unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        """Failsafe: cualquier excepción no manejada → 500 sanitizado."""
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        error_id = str(uuid.uuid4())
        logging.getLogger("sica_api").exception(
            "unhandled exception",
            extra={
                "request_id": request_id,
                "error_id": error_id,
                "exception_type": type(exc).__name__,
            },
        )
        return JSONResponse(
            status_code=500,
            headers={"X-Request-ID": request_id, "X-Error-ID": error_id},
            content={
                "error": "internal_error",
                "detail": "Error interno del servidor — citar error_id al pedir soporte.",
                "request_id": request_id,
                "error_id": error_id,
            },
        )

    return app


app = create_app()


def run() -> None:
    """Entry point para `sica-api` (project.scripts)."""
    import uvicorn

    uvicorn.run("sica_api.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    run()
