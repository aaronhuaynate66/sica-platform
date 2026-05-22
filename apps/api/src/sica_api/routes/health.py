"""GET /health — liveness + extractor-readiness check."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from sica_api import __version__
from sica_api.schemas import HealthResponse
from sica_api.settings import Settings, get_settings

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Liveness + readiness check.

    `status` siempre es "ok" si el proceso responde. `extractor_available`
    refleja si /extract puede servir requests (depende de ANTHROPIC_API_KEY).
    Probes de Kubernetes deben tratar HTTP 200 como liveness; el campo
    `extractor_available` se usa para readiness.
    """
    return HealthResponse(
        status="ok",
        version=__version__,
        extractor_available=settings.extractor_available,
    )
