"""Langfuse tracing para apps/api — trace padre del request HTTP.

Diseño (mirror del módulo `clinical_extractor.tracing`):

- ``get_langfuse_client()`` cached con ``lru_cache``. Retorna ``None``
  si la observability está deshabilitada (env vars faltantes) o si el
  SDK falla al inicializarse. **El API HTTP sigue respondiendo
  normalmente** — graceful degradation absoluta.

- ``start_extract_trace()`` crea un ``span`` root en Langfuse usando
  ``client.start_observation(as_type="span", ...)`` (API canónica en
  v3; ``client.trace()`` no existe en este SDK). El span devuelto se
  guarda en el ``trace_context`` para poder finalizarlo más tarde.

- ``finish_extract_trace()`` actualiza el span con outcome (success/error),
  output_summary, latencia, y llama ``span.end()`` + ``client.flush()``.
  No-op si el ``trace_context`` es ``None`` (caso: tracing deshabilitado).

- ``finish_extract_trace`` **nunca levanta**. Si Langfuse falla durante
  la finalización, se loggea como warning y se retorna — el response
  HTTP ya está armado para el cliente.

Forma del ``trace_context`` retornado por ``start_extract_trace``:

    {
      "trace_id": str,        # ID del trace en Langfuse, sirve como parent
      "span_id": str,         # ID del span root (parent_span_id para children)
      "span": LangfuseSpan,   # referencia viva al objeto SDK para .end() después
      "request_id": str,      # eco del request_id del API (correlación con logs)
    }

El extractor consume ``trace_id`` y ``span_id`` desde este dict (vía
``ExtractionRequest.parent_trace_id`` y ``parent_span_id``) y crea su
``generation`` como child del span root — produce jerarquía visible en
el dashboard.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langfuse import Langfuse

logger = logging.getLogger("sica_api.tracing")


@lru_cache(maxsize=1)
def get_langfuse_client() -> Langfuse | None:
    """Cliente Langfuse cached. ``None`` si deshabilitado o init falla."""
    try:
        from sica_api.settings import get_settings

        settings = get_settings()
        if not settings.langfuse_enabled:
            logger.info(
                "Langfuse tracing deshabilitado en apps/api "
                "(LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY no presentes)"
            )
            return None

        from langfuse import Langfuse

        client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_base_url,
            environment=settings.langfuse_tracing_environment,
        )
        logger.info(
            "Langfuse client inicializado en apps/api (env=%s, host=%s)",
            settings.langfuse_tracing_environment,
            settings.langfuse_base_url,
        )
        return client
    except Exception as exc:
        logger.warning("Langfuse client init falló en apps/api: %s", exc)
        return None


def start_extract_trace(
    *,
    request_id: str,
    pdf_filename: str | None = None,
    pdf_size_bytes: int | None = None,
    user_metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Inicia un span root en Langfuse para un request ``POST /extract``.

    Returns:
        Dict con ``trace_id``, ``span_id``, ``span`` (referencia viva), y
        ``request_id`` — pasable al extractor para que su generation cuelgue
        como child. ``None`` si tracing está deshabilitado o el SDK falla.
    """
    client = get_langfuse_client()
    if client is None:
        return None

    try:
        span = client.start_observation(
            name="api_extract_request",
            as_type="span",
            metadata={
                "request_id": request_id,
                "pdf_filename": pdf_filename or "uploaded_pdf",
                "pdf_size_bytes": pdf_size_bytes,
                "service": "sica-api",
                "endpoint": "POST /extract",
                **(user_metadata or {}),
            },
        )
        return {
            "trace_id": span.trace_id,
            "span_id": span.id,
            "span": span,
            "request_id": request_id,
        }
    except Exception as exc:
        logger.warning("start_extract_trace falló para %s: %s", request_id, exc)
        return None


def finish_extract_trace(
    trace_context: dict[str, Any] | None,
    *,
    success: bool,
    latency_ms: float,
    output_summary: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    """Marca el span root como terminado.

    No-op si ``trace_context`` es ``None``. Jamás levanta — si Langfuse
    falla en este punto, el response HTTP ya está armado y el cliente
    lo recibirá igual.
    """
    if trace_context is None:
        return

    client = get_langfuse_client()
    if client is None:
        return

    try:
        span = trace_context.get("span")
        if span is None:
            return
        span.update(
            output=output_summary,
            metadata={
                "latency_ms": latency_ms,
                "success": success,
                "error": error,
            },
            level="ERROR" if not success else "DEFAULT",
            status_message=error,
        )
        span.end()
        # Flush asíncrono — el SDK envía en background. En tests / smoke
        # damos un margen al SDK para que llegue.
        client.flush()
    except Exception as exc:
        logger.warning("finish_extract_trace falló: %s", exc)


def get_trace_id_from_context(trace_context: dict[str, Any] | None) -> str | None:
    """Extrae ``trace_id`` del contexto, ``None`` si falta o no hay tracing."""
    if trace_context is None:
        return None
    val = trace_context.get("trace_id")
    return val if isinstance(val, str) else None


def get_span_id_from_context(trace_context: dict[str, Any] | None) -> str | None:
    """Extrae ``span_id`` del contexto (parent_span_id para children)."""
    if trace_context is None:
        return None
    val = trace_context.get("span_id")
    return val if isinstance(val, str) else None
