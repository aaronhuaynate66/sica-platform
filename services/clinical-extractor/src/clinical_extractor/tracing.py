"""Integración Langfuse Cloud para observability de extracciones LLM.

Diseño:

- ``get_langfuse_client()`` es **cached**: la primera llamada inicializa
  el SDK; las subsecuentes devuelven la misma instancia. Si las env vars
  no están presentes, devuelve ``None`` y el resto del módulo es no-op.

- ``trace_extraction()`` **jamás levanta excepción**. Cualquier fallo
  interno del SDK o de la red queda atrapado, loggea warning, y retorna.
  Esto materializa la regla operativa: "tracing nunca rompe el extractor".

- ``shutdown_tracing()`` se llama al final de scripts CLI (o de la app)
  para forzar flush. En scripts long-running (servidor) se omite.

API:

    from clinical_extractor.tracing import trace_extraction

    trace_extraction(
        case_id="synthetic_case_01",
        model="claude-sonnet-4-5-20250929",
        provider_id="anthropic",
        input_tokens=1200,
        output_tokens=350,
        latency_ms=14_800,
        output_json={...},
        error=None,
    )

Convención de level Langfuse:
- ``DEFAULT`` (éxito).
- ``ERROR`` (con ``status_message=str(error)``) cuando la extracción falló.

Privacidad: ``output_json`` se envía a Langfuse Cloud (US region). Ver
ADR 0007 § Privacidad y PHI — actualmente sólo PDFs sintéticos; si en
algún momento se procesa PHI real, evaluar Langfuse self-hosted o
omitir el campo ``output_json``.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langfuse import Langfuse

logger = logging.getLogger("clinical_extractor.tracing")


@lru_cache(maxsize=1)
def get_langfuse_client() -> Langfuse | None:
    """Devuelve un cliente Langfuse listo, o ``None`` si tracing deshabilitado.

    El chequeo de las env vars y la inicialización del SDK corren una
    sola vez por proceso. Si algo falla (ImportError, credenciales mal
    formateadas, red), se loggea como warning y se devuelve ``None`` —
    el extractor sigue funcionando normalmente.
    """
    try:
        from clinical_extractor.settings import get_langfuse_settings

        settings = get_langfuse_settings()
        if not settings.enabled:
            logger.info(
                "Langfuse tracing deshabilitado (LANGFUSE_PUBLIC_KEY / "
                "LANGFUSE_SECRET_KEY no presentes en el entorno)"
            )
            return None

        from langfuse import Langfuse

        client = Langfuse(
            public_key=settings.public_key,
            secret_key=settings.secret_key,
            host=settings.base_url,
            environment=settings.tracing_environment,
            sample_rate=settings.sample_rate,
        )
        logger.info(
            "Langfuse client inicializado (env=%s, sample_rate=%s, host=%s)",
            settings.tracing_environment,
            settings.sample_rate,
            settings.base_url,
        )
        return client
    except Exception as exc:
        # Cualquier error en init NO debe romper el extractor.
        logger.warning("Langfuse client init falló: %s", exc)
        return None


def trace_extraction(
    *,
    case_id: str,
    model: str,
    provider_id: str,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cache_read_tokens: int | None = None,
    cache_write_tokens: int | None = None,
    latency_ms: float | None = None,
    output_json: dict[str, Any] | None = None,
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
    parent_trace_id: str | None = None,
    parent_span_id: str | None = None,
) -> None:
    """Registra una extracción en Langfuse como ``generation`` observation.

    Esta función **nunca** levanta. Si Langfuse no está configurado o el
    SDK falla, se loggea como warning y se retorna.

    Args:
        case_id: ID estable del caso (filename sin extensión, UUID, etc.).
            Se usa como prefijo del trace name y va en ``metadata.case_id``.
        model: ID exacto del modelo Anthropic invocado.
        provider_id: ``anthropic`` | ``vertex-medgemma`` | etc.
        input_tokens: Tokens consumidos de input. Se usa para cost calc.
        output_tokens: Tokens generados.
        cache_read_tokens: Tokens leídos del prompt cache (Anthropic).
        cache_write_tokens: Tokens escritos al prompt cache.
        latency_ms: Latencia end-to-end de la extracción (ms).
        output_json: Output estructurado (``ObstetricSummary.model_dump()``).
            Va al campo ``output`` del trace — visible en el dashboard.
        error: Si la extracción falló, mensaje corto. Setea ``level=ERROR``
            y ``status_message=error`` en el trace.
        metadata: Pares clave/valor adicionales. Se mergean con los
            defaults (``provider_id``, ``extractor_version``, etc.).
        parent_trace_id: Si está presente, la generation se crea como child
            del trace identificado por este ID (vía ``trace_context``).
            Permite que el dashboard muestre jerarquía padre-hijo cuando
            el caller (apps/api, orquestador) ya inició un trace propio.
            Ver ADR 0007 § Trace context propagation.
        parent_span_id: ``span.id`` del span padre. Opcional — afina la
            anidación visual cuando hay múltiples spans en el mismo trace.
    """
    client = get_langfuse_client()
    if client is None:
        return  # No-op.

    try:
        from clinical_extractor import __version__
        from clinical_extractor.pricing import calculate_cost_usd

        # Cost calculation — None si modelo no está en la tabla de pricing.
        cost_usd: float | None = None
        if input_tokens is not None and output_tokens is not None:
            cost_usd = calculate_cost_usd(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read_tokens or 0,
                cache_write_tokens=cache_write_tokens or 0,
            )

        # Metadata mergeada. NUNCA incluir contenido del PDF ni PHI.
        full_metadata: dict[str, Any] = {
            "case_id": case_id,
            "provider_id": provider_id,
            "extractor_version": __version__,
        }
        if latency_ms is not None:
            full_metadata["latency_ms"] = latency_ms
        if metadata:
            full_metadata.update(metadata)

        # Usage details: shape esperado por Langfuse (claves "input"/"output"
        # + cache fields). Sólo incluir keys con valor real.
        usage_details: dict[str, int] = {}
        if input_tokens is not None:
            usage_details["input"] = int(input_tokens)
        if output_tokens is not None:
            usage_details["output"] = int(output_tokens)
        if cache_read_tokens:
            usage_details["cache_read_input_tokens"] = int(cache_read_tokens)
        if cache_write_tokens:
            usage_details["cache_creation_input_tokens"] = int(cache_write_tokens)

        cost_details: dict[str, float] | None = None
        if cost_usd is not None:
            cost_details = {"total": cost_usd}

        # ``trace_context`` enchufa esta generation bajo un trace existente
        # cuando el caller propagó IDs. TypedDict shape:
        # {"trace_id": str, "parent_span_id": str (NotRequired)}.
        trace_context: dict[str, str] | None = None
        if parent_trace_id:
            trace_context = {"trace_id": parent_trace_id}
            if parent_span_id:
                trace_context["parent_span_id"] = parent_span_id

        # ``start_observation(as_type="generation")`` es la API canónica en
        # v3 (start_generation está deprecated). El SDK declara overloads
        # por cada literal de ``as_type`` (span, generation, embedding,
        # evaluator, guardrail, ...) y con ``trace_context`` opcional
        # mypy strict no logra elegir uno — "too many unions". Suprimimos
        # el error puntualmente; runtime es válido y los tests lo cubren.
        kwargs: dict[str, Any] = {
            "name": f"extract_{case_id}",
            "as_type": "generation",
            "model": model,
            "output": output_json,
            "metadata": full_metadata,
            "usage_details": usage_details or None,
            "cost_details": cost_details,
            "level": "ERROR" if error else "DEFAULT",
            "status_message": error,
        }
        if trace_context is not None:
            kwargs["trace_context"] = trace_context
        generation = client.start_observation(**kwargs)
        generation.end()

        # Flush asíncrono — la corrida CLI llama shutdown_tracing() para
        # garantizar entrega; en server long-running el SDK flushea en
        # background cada N segundos.
        client.flush()

    except Exception as exc:
        # Cualquier error de SDK / red / serialización queda contenido.
        logger.warning("Langfuse trace falló para case_id=%s: %s", case_id, exc)


def shutdown_tracing() -> None:
    """Flush + shutdown del cliente Langfuse.

    Llamar al final de scripts CLI para garantizar que los traces lleguen
    al backend antes de que el proceso muera. Idempotente — si tracing
    está deshabilitado, no hace nada.
    """
    client = get_langfuse_client()
    if client is None:
        return
    try:
        client.shutdown()
    except Exception as exc:
        logger.warning("Langfuse shutdown falló: %s", exc)
