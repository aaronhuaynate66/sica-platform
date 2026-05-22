"""GET /health — liveness + extractor-readiness check."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from sica_api import __version__
from sica_api.schemas import HealthResponse
from sica_api.settings import Settings, get_settings

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Liveness + readiness check.

    Diseñado para health-check probes (Render, Kubernetes, etc.):
    - Sin llamadas a Anthropic ni a la base de datos.
    - Sin I/O bloqueante.
    - Latencia objetivo <100ms.

    `status` siempre es "ok" si el proceso responde. `extractor_available`
    refleja si /extract puede servir requests (depende sólo de que la env
    var ANTHROPIC_API_KEY esté presente — no la valida contra Anthropic).
    Render usa HTTP 200 como liveness; el campo `extractor_available` se
    consume desde la UI para alternar entre modo live y demo.
    """
    return HealthResponse(
        status="ok",
        version=__version__,
        extractor_available=settings.extractor_available,
        timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
