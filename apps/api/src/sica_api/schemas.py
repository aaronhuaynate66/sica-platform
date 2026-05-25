"""Request / response schemas de la API.

NOTA: el schema de ObstetricSummary vive en `clinical_extractor.schemas`.
La API no lo re-declara — re-exporta vía dependency. Si el contrato cambia,
cambia ahí y la API queda en sync automáticamente.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Capacidades reconocidas por el endpoint /providers. Mantener cerrado por
# Literal evita que un provider declare una capability inventada — toda
# adición pasa por revisión y por update del frontend que las lee.
ProviderCapability = Literal["tool_use", "vision", "streaming", "long_context"]


class HealthResponse(BaseModel):
    """Body de respuesta para GET /health.

    Diseñado para Render health checks: ejecución <100ms, sin llamadas
    de red, sin tocar Anthropic. Sólo introspección local.
    """

    model_config = ConfigDict(extra="forbid")

    status: str = Field(description="'ok' si el proceso está vivo.")
    version: str = Field(description="Versión semántica del paquete sica-api.")
    extractor_available: bool = Field(
        description=(
            "True si el extractor está listo para servir requests "
            "(ANTHROPIC_API_KEY presente). False bloquea /extract."
        ),
    )
    timestamp: str = Field(
        description="Momento UTC ISO 8601 en el que el servidor respondió.",
    )


class ModelInfo(BaseModel):
    """Un modelo configurado según ADR 0004."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Identificador estable del modelo.")
    provider: str = Field(description="Proveedor: anthropic | google | local | etc.")
    type: str = Field(description="cloud | local")
    phi_allowed: bool = Field(
        description="True si el modelo puede procesar PHI real bajo ADR 0003/0004.",
    )
    active: bool = Field(
        description="True si el modelo está marcado como default activo en R0+.",
    )
    role: str = Field(
        description="Rol según ADR 0004 Nivel 1: default | fallback | dev_only | prohibited.",
    )
    notes: str = Field(
        default="",
        description="Notas operativas relevantes.",
    )
    is_available: bool = Field(
        default=False,
        description=(
            "True si hay un LLMProvider registrado, soporta este modelo y "
            "reporta is_available() == True (credenciales presentes). "
            "Distinto de 'active' — que es decisión de política."
        ),
    )
    provider_id: str | None = Field(
        default=None,
        description=(
            "ID del LLMProvider que atiende este modelo (anthropic, "
            "vertex-medgemma, etc.). None si no hay provider implementado aún."
        ),
    )


class ProviderModelInfo(BaseModel):
    """Modelo dentro de un provider, en el shape rico de GET /providers."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Identificador del modelo (ej. claude-sonnet-4-5-20250929).")
    is_default: bool = Field(
        description=(
            "True si es el primer modelo declarado en ``provider.supported_models``. "
            "Convención del registry: el primero es el default operativo del provider."
        ),
    )


class ProviderInfo(BaseModel):
    """Vista rica de un LLMProvider más sus modelos."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str = Field(description="ID estable: anthropic, vertex-medgemma, etc.")
    is_available: bool = Field(
        description=(
            "True si ``provider.is_available()`` retornó True en runtime "
            "(credenciales presentes, dependencias listas)."
        ),
    )
    available_note: str | None = Field(
        default=None,
        description=(
            "Cuando ``is_available`` es False, explica por qué (env vars faltantes, "
            "stub pendiente). None cuando el provider está operativo."
        ),
    )
    models: list[ProviderModelInfo] = Field(
        default_factory=list,
        description="Modelos que este provider declara en ``supported_models``.",
    )
    capabilities: list[ProviderCapability] = Field(
        default_factory=list,
        description=(
            "Capacidades estáticas declaradas para el provider. Hoy es metadata "
            "del endpoint (PROVIDER_CAPABILITIES); en R1 se mueve a metadata del "
            "LLMProvider base."
        ),
    )


class ProvidersResponse(BaseModel):
    """Body de respuesta de GET /providers — shape rico agrupado por provider."""

    model_config = ConfigDict(extra="forbid")

    providers: list[ProviderInfo] = Field(
        default_factory=list,
        description="Todos los providers registrados, disponibles o no.",
    )
    default_provider_id: str = Field(
        description=(
            "Provider que el extractor usa por default en R0 (ADR 0004). "
            "Distinto del modelo default — ese vive en ``models[].is_default`` "
            "dentro del provider correspondiente."
        ),
    )
    total_providers: int = Field(
        ge=0,
        description="Cuántos providers están registrados (independiente de availability).",
    )
    available_count: int = Field(
        ge=0,
        description="Cuántos providers reportan ``is_available()`` True en este runtime.",
    )


class ErrorResponse(BaseModel):
    """Respuesta de error estandarizada — NO incluye stack trace ni PHI."""

    model_config = ConfigDict(extra="forbid")

    error: str = Field(description="Código de error legible.")
    detail: str = Field(description="Descripción breve del error.")
    request_id: str = Field(description="UUID para correlación con logs.")
    error_id: str | None = Field(
        default=None,
        description="UUID para errores 5xx — el cliente lo cita al pedir soporte.",
    )
