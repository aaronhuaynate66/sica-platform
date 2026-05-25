"""Adapter pattern multi-provider para clinical-extractor.

Refactor del clinical-extractor para que soporte múltiples LLM providers
sin código duplicado. Ver ADR 0004 (model routing policy) para la política
que esta arquitectura implementa.

Providers en R0:
- ``AnthropicProvider`` — Claude (default, production-ready en datos sintéticos).
- ``VertexMedGemmaProvider`` — MedGemma 4B vía Vertex AI (stub, pendiente
  GCP credentials — ver issue #12).

Cómo agregar un provider nuevo:
1. Crear ``providers/my_provider.py`` heredando de ``LLMProvider``.
2. Implementar los métodos abstractos: ``provider_id``, ``supported_models``,
   ``is_available``, ``extract``.
3. Registrarlo en ``ProviderRegistry._register_defaults()`` o vía
   ``registry.register(MyProvider())`` desde afuera.

El selector de provider en runtime se hace por ``model_id``. Cada provider
declara qué models soporta vía ``supported_models``.
"""

from __future__ import annotations

from clinical_extractor.providers.anthropic_provider import AnthropicProvider
from clinical_extractor.providers.base import (
    ExtractionRequest,
    ExtractionResponse,
    LLMProvider,
    ProviderNotAvailableError,
)
from clinical_extractor.providers.registry import DEFAULT_REGISTRY, ProviderRegistry
from clinical_extractor.providers.vertex_medgemma_provider import VertexMedGemmaProvider

__all__ = [
    "DEFAULT_REGISTRY",
    "AnthropicProvider",
    "ExtractionRequest",
    "ExtractionResponse",
    "LLMProvider",
    "ProviderNotAvailableError",
    "ProviderRegistry",
    "VertexMedGemmaProvider",
]
