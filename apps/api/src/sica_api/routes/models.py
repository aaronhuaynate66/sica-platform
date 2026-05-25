"""GET /models — lista de modelos según ADR 0004 enriquecida con runtime state.

Lista declarativa (hardcoded — refleja ADR 0004 Nivel 1) cruzada con el
registry de providers del clinical-extractor:

- Los campos ``id``, ``provider``, ``type``, ``phi_allowed``, ``active``,
  ``role`` y ``notes`` salen de la política estática.
- ``is_available`` y ``provider_id`` se calculan en runtime contra
  ``DEFAULT_REGISTRY`` del extractor — refleja si hay un provider real
  registrado, soporta el modelo y reporta credenciales presentes.

Para modelos que aún no tienen provider implementado (Gemini, Document AI,
MedSigLIP), ``is_available=False`` y ``provider_id=None`` — quedará en
``True`` cuando los providers se agreguen al registry en sesiones futuras.
"""

from __future__ import annotations

from fastapi import APIRouter

from sica_api.schemas import ModelInfo

router = APIRouter(tags=["models"])


# Lista derivada de ADR 0004 Nivel 1.
# El orden refleja prioridad de evaluación, no de uso.
_MODELS_POLICY: list[dict] = [
    {
        "id": "claude-sonnet-4-5-20250929",
        "provider": "anthropic",
        "type": "cloud",
        "phi_allowed": False,
        "active": True,
        "role": "dev_only",
        "notes": (
            "Default actual del clinical-extractor en R0 sobre datos sintéticos. "
            "Vetado para PHI real por ADR 0003. Reemplazo planificado por "
            "MedGemma 4B local cuando #12 cierre."
        ),
    },
    {
        "id": "claude-opus-4-7",
        "provider": "anthropic",
        "type": "cloud",
        "phi_allowed": False,
        "active": False,
        "role": "dev_only",
        "notes": (
            "Modelo Claude más capaz — disponible para razonamiento complejo en "
            "desarrollo. Vetado para PHI real (ADR 0003)."
        ),
    },
    {
        "id": "claude-haiku-4-5-20251001",
        "provider": "anthropic",
        "type": "cloud",
        "phi_allowed": False,
        "active": False,
        "role": "dev_only",
        "notes": (
            "Modelo Claude rápido — útil para iteración de prompts y costos bajos "
            "en datos sintéticos."
        ),
    },
    {
        "id": "medgemma-4b-it",
        "provider": "google",
        "type": "local",
        "phi_allowed": True,
        "active": False,
        "role": "default",
        "notes": (
            "Default planificado para resumen obstétrico y care gaps en R1+. "
            "Viabilidad técnica en evaluación (issue #12). Stub registrado en el "
            "extractor — implementación real pendiente sesión con GCP."
        ),
    },
    {
        "id": "medgemma-27b-text",
        "provider": "google",
        "type": "local",
        "phi_allowed": True,
        "active": False,
        "role": "default",
        "notes": (
            "Razonamiento clínico complejo (handoff materno-neonatal, brief "
            "preanestésico). Activación condicionada a hardware disponible."
        ),
    },
    {
        "id": "gemini-2.5-flash",
        "provider": "google",
        "type": "cloud",
        "phi_allowed": True,
        "active": False,
        "role": "fallback",
        "notes": (
            "Default para extracción estructurada de PDF nativo (visión). "
            "Fallback para contextos largos. Requiere DPA peruano vigente."
        ),
    },
    {
        "id": "gemini-2.5-pro",
        "provider": "google",
        "type": "cloud",
        "phi_allowed": True,
        "active": False,
        "role": "fallback",
        "notes": "Fallback para razonamiento complejo si MedGemma 27B no disponible.",
    },
    {
        "id": "document-ai-v1",
        "provider": "google",
        "type": "cloud",
        "phi_allowed": True,
        "active": False,
        "role": "default",
        "notes": "OCR de PDFs escaneados / manuscritos médicos. Requiere DPA.",
    },
    {
        "id": "medsiglip",
        "provider": "google",
        "type": "local",
        "phi_allowed": True,
        "active": False,
        "role": "default",
        "notes": "Embeddings visuales para retrieval (ecografías, reportes con imagen).",
    },
]


def _build_models_with_runtime_state() -> list[ModelInfo]:
    """Combina política estática + estado runtime del registry de providers.

    El import del registry se hace dentro de la función para que tests del API
    que no tengan instalado el extractor no fallen al cargar este módulo.
    Cuando el extractor está disponible, cada modelo se enriquece con
    ``is_available`` y ``provider_id`` reales.
    """
    try:
        from clinical_extractor.providers import DEFAULT_REGISTRY
    except ImportError:
        registry = None
    else:
        registry = DEFAULT_REGISTRY

    out: list[ModelInfo] = []
    for entry in _MODELS_POLICY:
        is_available = False
        provider_id: str | None = None
        if registry is not None:
            provider = registry.get_for_model(entry["id"])
            if provider is not None:
                provider_id = provider.provider_id
                is_available = provider.is_available()
        out.append(
            ModelInfo(
                **entry,
                is_available=is_available,
                provider_id=provider_id,
            )
        )
    return out


@router.get("/models", response_model=list[ModelInfo])
async def list_models() -> list[ModelInfo]:
    """Lista declarativa de modelos configurados según ADR 0004.

    Cada item incluye además estado runtime de disponibilidad (``is_available``,
    ``provider_id``) calculado contra el registry del clinical-extractor.
    """
    return _build_models_with_runtime_state()
