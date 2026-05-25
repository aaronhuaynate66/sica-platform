"""Registry central de LLM providers.

Una instancia singleton (``DEFAULT_REGISTRY``) sirve como punto de entrada
desde el extractor core. Tests crean instancias propias para aislamiento.

Resolución por ``model_id``: el extractor pide ``get_for_model(model_id)``
y el registry devuelve el provider que declara soportarlo. Si dos providers
declaran el mismo model_id (raro), gana el primero registrado — por eso
``_register_defaults`` registra ``AnthropicProvider`` antes que el stub de
MedGemma (irrelevante hoy, importante mañana).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from clinical_extractor.providers.anthropic_provider import AnthropicProvider
from clinical_extractor.providers.vertex_medgemma_provider import (
    VertexMedGemmaProvider,
)

if TYPE_CHECKING:
    from clinical_extractor.providers.base import LLMProvider


class ProviderRegistry:
    """Registro central de providers disponibles."""

    def __init__(self, *, register_defaults: bool = True) -> None:
        self._providers: dict[str, LLMProvider] = {}
        if register_defaults:
            self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(AnthropicProvider())
        self.register(VertexMedGemmaProvider())

    def register(self, provider: LLMProvider) -> None:
        """Agrega o reemplaza un provider en el registry.

        Reemplazar es idempotente — útil para tests que inyectan mocks.
        """
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> LLMProvider:
        """Devuelve provider por su ``provider_id``.

        Raises:
            ValueError: si el provider_id no está registrado.
        """
        if provider_id not in self._providers:
            msg = (
                f"Provider '{provider_id}' no registrado. "
                f"Disponibles: {sorted(self._providers.keys())}"
            )
            raise ValueError(msg)
        return self._providers[provider_id]

    def get_for_model(self, model_id: str) -> LLMProvider | None:
        """Encuentra el provider que soporta un ``model_id`` dado.

        Recorre los providers en orden de registro y devuelve el primero que
        declara el modelo en ``supported_models``. Devuelve ``None`` si
        ningún provider lo soporta — el caller decide si ese es error fatal
        o degradación.
        """
        for provider in self._providers.values():
            if model_id in provider.supported_models:
                return provider
        return None

    def list_available(self) -> list[LLMProvider]:
        """Providers con ``is_available() == True`` (en orden de registro)."""
        return [p for p in self._providers.values() if p.is_available()]

    def list_all(self) -> list[LLMProvider]:
        """Todos los providers registrados, disponibles o no."""
        return list(self._providers.values())


# Singleton consumido por extractor.py y apps/api routes/models.py.
# Construirlo perezosamente NO conviene aquí: la construcción es barata
# y validamos al import-time que los providers se instancien sin errores.
DEFAULT_REGISTRY = ProviderRegistry()
