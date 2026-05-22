"""GET /models — lista declarada de modelos según ADR 0004.

Esta lista es **estática** en R0: refleja la política de routing
formalizada en `docs/decisions/0004-model-routing-policy.md`. Cuando el
orquestador real entre en R1+, este endpoint pasará a leer del registry
vivo en vez del array hard-coded. Por ahora sirve como contrato estable
para la UI y para asesores que pregunten "qué modelos usa SICA".
"""

from __future__ import annotations

from fastapi import APIRouter

from sica_api.schemas import ModelInfo

router = APIRouter(tags=["models"])


# Lista derivada de ADR 0004 Nivel 1.
_MODELS: list[ModelInfo] = [
    ModelInfo(
        id="claude-sonnet-4-5-20250929",
        provider="anthropic",
        type="cloud",
        phi_allowed=False,
        active=True,
        role="dev_only",
        notes=(
            "Default actual del clinical-extractor en R0 sobre datos sintéticos. "
            "Vetado para PHI real por ADR 0003. Reemplazo planificado por "
            "MedGemma 4B local cuando #12 cierre."
        ),
    ),
    ModelInfo(
        id="medgemma-4b",
        provider="google",
        type="local",
        phi_allowed=True,
        active=False,
        role="default",
        notes=(
            "Default planificado para resumen obstétrico y care gaps en R1+. "
            "Viabilidad técnica en evaluación (issue #12). No activo en R0."
        ),
    ),
    ModelInfo(
        id="medgemma-27b-text",
        provider="google",
        type="local",
        phi_allowed=True,
        active=False,
        role="default",
        notes=(
            "Razonamiento clínico complejo (handoff materno-neonatal, brief "
            "preanestésico). Activación condicionada a hardware disponible."
        ),
    ),
    ModelInfo(
        id="gemini-2.5-flash",
        provider="google",
        type="cloud",
        phi_allowed=True,
        active=False,
        role="fallback",
        notes=(
            "Default para extracción estructurada de PDF nativo (visión). "
            "Fallback para contextos largos. Requiere DPA peruano vigente."
        ),
    ),
    ModelInfo(
        id="gemini-2.5-pro",
        provider="google",
        type="cloud",
        phi_allowed=True,
        active=False,
        role="fallback",
        notes="Fallback para razonamiento complejo si MedGemma 27B no disponible.",
    ),
    ModelInfo(
        id="document-ai-v1",
        provider="google",
        type="cloud",
        phi_allowed=True,
        active=False,
        role="default",
        notes="OCR de PDFs escaneados / manuscritos médicos. Requiere DPA.",
    ),
    ModelInfo(
        id="medsiglip",
        provider="google",
        type="local",
        phi_allowed=True,
        active=False,
        role="default",
        notes="Embeddings visuales para retrieval (ecografías, reportes con imagen).",
    ),
]


@router.get("/models", response_model=list[ModelInfo])
async def list_models() -> list[ModelInfo]:
    """Lista declarativa de modelos configurados según ADR 0004."""
    return _MODELS
