"""GET /providers — shape rico agrupado por provider.

Complementa ``/models`` (lista plana retrocompatible con el frontend
actual) con una vista jerárquica:

    provider → models → capabilities + availability

Diseñado para UIs nuevas o dashboards que necesiten conocer qué
provider atiende qué modelo, qué capabilities tiene y por qué un
provider está marcado como no disponible.

Implementación:

- Itera sobre ``DEFAULT_REGISTRY.list_all()`` (API pública del registry).
- Capabilities se mantienen como metadata estática **acá** mientras
  el ``LLMProvider`` base no las exponga. Cuando se mueva a la
  interface del provider (TODO R1), este módulo lee de allí en
  lugar del dict local.
- Notas de no-disponibilidad: dict estático por ``provider_id``. Para
  providers operativos, queda ``None``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter

from sica_api.schemas import (
    ProviderCapability,
    ProviderInfo,
    ProviderModelInfo,
    ProvidersResponse,
)

if TYPE_CHECKING:
    from clinical_extractor.providers.base import LLMProvider


router = APIRouter(prefix="/providers", tags=["providers"])

# Provider default según ADR 0004 Nivel 1 — en R0 sobre datos sintéticos
# el extractor llama a Anthropic Claude Sonnet 4.5. Cambiar este string
# requiere ADR (no es valor cosmético).
DEFAULT_PROVIDER_ID = "anthropic"

# Capabilities estáticas por provider.
# TODO(R1): mover esta metadata a la interface ``LLMProvider`` (propiedad
# ``capabilities``) para que cada provider declare las suyas. Mientras tanto,
# el endpoint las mantiene acá porque acoplar la interface ahora dispararía
# un refactor del extractor que no aporta valor en R0.
PROVIDER_CAPABILITIES: dict[str, list[ProviderCapability]] = {
    "anthropic": ["tool_use", "vision", "streaming", "long_context"],
    "vertex-medgemma": [],  # stub — capabilities reales cuando #12 cierre
}

# Mensaje humano cuando ``is_available()`` retorna False. Provee contexto al
# frontend (qué falta para que el provider quede operativo).
PROVIDER_UNAVAILABLE_NOTES: dict[str, str] = {
    "anthropic": (
        "ANTHROPIC_API_KEY no configurada en este entorno. Setear la env var y reiniciar la app."
    ),
    "vertex-medgemma": (
        "Pendiente: GCP credentials no configuradas y extract() sin implementar. "
        "Ver issue #12 y vertex_medgemma_provider.py."
    ),
}


def _default_model_id(provider: LLMProvider) -> str | None:
    """Primer modelo declarado en ``supported_models`` (convención del registry)."""
    return provider.supported_models[0] if provider.supported_models else None


def _build_provider_info(provider: LLMProvider) -> ProviderInfo:
    default_model_id = _default_model_id(provider)
    models = [
        ProviderModelInfo(id=model_id, is_default=(model_id == default_model_id))
        for model_id in provider.supported_models
    ]
    is_available = provider.is_available()
    note = None if is_available else PROVIDER_UNAVAILABLE_NOTES.get(provider.provider_id)
    return ProviderInfo(
        provider_id=provider.provider_id,
        is_available=is_available,
        available_note=note,
        models=models,
        capabilities=PROVIDER_CAPABILITIES.get(provider.provider_id, []),
    )


@router.get("", response_model=ProvidersResponse)
async def list_providers() -> ProvidersResponse:
    """Retorna providers + modelos + availability en shape rico.

    Convive con ``GET /models`` (lista plana). Usar este endpoint cuando
    el cliente necesita conocer estructura completa por provider; ``/models``
    sigue siendo la lista plana retrocompatible.
    """
    # Import diferido: si el extractor no está instalado (entornos minimal
    # como CI del front), el endpoint devuelve lista vacía en vez de 500.
    try:
        from clinical_extractor.providers import DEFAULT_REGISTRY
    except ImportError:
        return ProvidersResponse(
            providers=[],
            default_provider_id=DEFAULT_PROVIDER_ID,
            total_providers=0,
            available_count=0,
        )

    providers_info = [_build_provider_info(p) for p in DEFAULT_REGISTRY.list_all()]
    return ProvidersResponse(
        providers=providers_info,
        default_provider_id=DEFAULT_PROVIDER_ID,
        total_providers=len(providers_info),
        available_count=sum(1 for p in providers_info if p.is_available),
    )
