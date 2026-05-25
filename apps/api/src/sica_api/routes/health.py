"""GET /health — liveness + extractor-readiness check."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from sica_api import __version__
from sica_api.extractor_status import extractor_module_available
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
    es True sólo si **ambas** condiciones se cumplen:

    1. ``ANTHROPIC_API_KEY`` presente en el entorno (env var).
    2. El paquete ``clinical_extractor`` está instalado e importable.

    Si (1) falla → ``/extract`` responde 503. Si (2) falla → ``/extract``
    devolvería 500 al primer request porque el import dinámico revienta.
    Reportar ``true`` cuando (2) falla sería una mentira silenciosa
    (situación que descubrimos en producción: render.yaml no instalaba
    el extractor y el health-check decía OK igual).

    Render usa HTTP 200 como liveness; el campo se consume desde la UI
    para alternar entre modo live y demo.
    """
    extractor_ready = settings.extractor_available and extractor_module_available()
    return HealthResponse(
        status="ok",
        version=__version__,
        extractor_available=extractor_ready,
        timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
