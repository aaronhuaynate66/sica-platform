"""Request / response schemas de la API.

NOTA: el schema de ObstetricSummary vive en `clinical_extractor.schemas`.
La API no lo re-declara — re-exporta vía dependency. Si el contrato cambia,
cambia ahí y la API queda en sync automáticamente.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Body de respuesta para GET /health."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(description="'ok' si el proceso está vivo.")
    version: str = Field(description="Versión semántica del paquete sica-api.")
    extractor_available: bool = Field(
        description=(
            "True si el extractor está listo para servir requests "
            "(ANTHROPIC_API_KEY presente). False bloquea /extract."
        ),
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
        description="True si el modelo está disponible en runtime.",
    )
    role: str = Field(
        description="Rol según ADR 0004 Nivel 1: default | fallback | dev_only | prohibited.",
    )
    notes: str = Field(
        default="",
        description="Notas operativas relevantes.",
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
