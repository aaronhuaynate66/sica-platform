"""Lógica core del clinical-extractor: PDF → ObstetricSummary.

Multi-provider (R0 — Bloque E):

- **Adapter pattern.** El extractor selecciona un ``LLMProvider`` por
  ``model_id`` a través de ``DEFAULT_REGISTRY``. Cada provider encapsula
  retry, timeout, auth y manejo de errores específicos del SDK.
- **API pública estable.** ``extract_from_pdf`` mantiene su firma — los
  clientes existentes (apps/api, CLI, batch) siguen funcionando sin cambio
  con el default Claude Sonnet.
- **Telemetría JSON-line.** Un único registro por extracción con
  operation_id, latencia, retry count, token usage, modelo, prompt version,
  provider_id. NUNCA contenido del PDF ni PHI.

Cuando el modelo solicitado no tiene provider asociado (típico antes del
thursday — pedir ``medgemma-4b-it`` con stub no implementado), se levanta
``ExtractionError`` con mensaje claro y sugerencia de fallback.
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from clinical_extractor import telemetry
from clinical_extractor.prompts import get_active_prompt
from clinical_extractor.providers import (
    DEFAULT_REGISTRY,
    AnthropicProvider,
    ExtractionRequest,
    ProviderNotAvailableError,
)
from clinical_extractor.providers.anthropic_provider import (
    AnthropicExtractionError,
)
from clinical_extractor.schemas import ObstetricSummary

if TYPE_CHECKING:
    from pathlib import Path

    import anthropic

    from clinical_extractor.prompts import VersionedPrompt
    from clinical_extractor.providers.base import LLMProvider

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT_SECONDS = 60.0

# Retry policy defaults — overridables vía argumentos o env vars.
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_BACKOFF_SECONDS = 1.0
DEFAULT_MAX_BACKOFF_SECONDS = 16.0


class ExtractionError(RuntimeError):
    """Error en la pipeline de extracción.

    Cualquier fallo (PDF ilegible, modelo no devolvió tool_use, validación
    Pydantic falló, retries agotados, etc.) se levanta como esta excepción
    con contexto.
    """


def _read_pdf_text(pdf_path: Path) -> tuple[str, int]:
    """Extrae texto plano de un PDF nativo. Devuelve (texto, num_páginas).

    Para PDFs escaneados sin capa de texto, devuelve string vacío o
    fragmentos sueltos — caso en el cual habría que enrutar a OCR (no en R0).
    """
    # Import diferido evita coste cuando se mockea el extractor en tests.
    import pypdf

    if not pdf_path.exists():
        msg = f"PDF no existe: {pdf_path}"
        raise ExtractionError(msg)

    if pdf_path.suffix.lower() != ".pdf":
        msg = f"Archivo no es PDF: {pdf_path}"
        raise ExtractionError(msg)

    try:
        reader = pypdf.PdfReader(str(pdf_path))
    except Exception as exc:
        msg = f"No se pudo leer el PDF {pdf_path}: {exc}"
        raise ExtractionError(msg) from exc

    pages_text: list[str] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            msg = f"Error extrayendo texto de página {i}: {exc}"
            raise ExtractionError(msg) from exc
        pages_text.append(f"[Página {i}]\n{text}")

    full_text = "\n\n".join(pages_text).strip()
    if not full_text:
        msg = (
            f"El PDF {pdf_path} no devolvió texto extraíble. "
            "Puede ser un PDF escaneado sin capa de texto — requiere OCR (fuera de scope R0)."
        )
        raise ExtractionError(msg)
    return full_text, len(reader.pages)


def _resolve_provider(model_id: str, client: anthropic.Anthropic | None) -> LLMProvider:
    """Resuelve el provider para ``model_id``.

    Si se inyecta ``client`` (tests/dependency injection), siempre se
    devuelve un ``AnthropicProvider`` ad-hoc con ese cliente — mantiene
    retrocompatibilidad con tests que inyectaban el cliente directamente.
    """
    if client is not None:
        return AnthropicProvider(client=client)

    provider = DEFAULT_REGISTRY.get_for_model(model_id)
    if provider is None:
        msg = (
            f"No hay provider registrado que soporte el modelo '{model_id}'. "
            f"Modelos soportados: "
            f"{sorted(m for p in DEFAULT_REGISTRY.list_all() for m in p.supported_models)}"
        )
        raise ExtractionError(msg)
    return provider


def extract_from_pdf(
    pdf_path: Path,
    *,
    model: str | None = None,
    max_tokens: int | None = None,
    client: anthropic.Anthropic | None = None,
    prompt: VersionedPrompt | None = None,
    max_retries: int | None = None,
    initial_backoff: float | None = None,
    max_backoff: float | None = None,
    timeout_seconds: float | None = None,
) -> ObstetricSummary:
    """Extrae un ``ObstetricSummary`` desde un PDF nativo de historia obstétrica.

    Args:
        pdf_path: Ruta al PDF.
        model: ID del modelo. Default: env ``CLAUDE_MODEL`` o claude-sonnet-4-5.
            El registry resuelve qué provider lo atiende.
        max_tokens: Máximo de tokens de salida. Default: env CLAUDE_MAX_TOKENS o 4096.
        client: Cliente Anthropic preconfigurado (útil para tests). Si se inyecta,
            fuerza el uso de AnthropicProvider — ignora ``model`` si no es Claude.
        prompt: Versión del prompt a usar. Si None, se usa la activa por default.
        max_retries: Reintentos en errores transitorios. Default: env o 3.
        initial_backoff: Espera inicial entre reintentos en segundos.
        max_backoff: Tope del backoff exponencial en segundos.
        timeout_seconds: Timeout total por request al modelo.

    Returns:
        ObstetricSummary validado.

    Raises:
        ExtractionError: si el PDF no se puede leer, si el modelo no responde
            como se espera, si los retries se agotan, si el output falla
            validación Pydantic, o si no hay provider para ``model``.
        ProviderNotAvailableError: si el provider seleccionado no está
            configurado (ej. ``ANTHROPIC_API_KEY`` ausente).

    Telemetría: emite un registro JSON-line al logger
    ``clinical_extractor.telemetry`` con campos: timestamp, operation_id,
    provider_id, model_used, prompt_version, latency_ms, retry_count,
    token_usage, success, error_type.
    """
    resolved_model: str = model or os.getenv("CLAUDE_MODEL") or DEFAULT_MODEL
    resolved_max_tokens = max_tokens or int(
        os.getenv("CLAUDE_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))
    )
    resolved_prompt = prompt or get_active_prompt()
    resolved_max_retries = (
        max_retries
        if max_retries is not None
        else int(os.getenv("CLAUDE_MAX_RETRIES", str(DEFAULT_MAX_RETRIES)))
    )
    resolved_initial_backoff = initial_backoff or float(
        os.getenv("CLAUDE_INITIAL_BACKOFF", str(DEFAULT_INITIAL_BACKOFF_SECONDS))
    )
    resolved_max_backoff = max_backoff or float(
        os.getenv("CLAUDE_MAX_BACKOFF", str(DEFAULT_MAX_BACKOFF_SECONDS))
    )
    resolved_timeout = timeout_seconds or float(
        os.getenv("CLAUDE_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
    )

    operation_id = str(uuid.uuid4())
    started = time.perf_counter()
    pdf_size_bytes: int | None = None
    pages_extracted: int | None = None
    retry_count = 0
    token_usage: dict[str, int] | None = None
    error_type: str | None = None
    provider_id: str | None = None
    success = False

    try:
        # 1. Read PDF
        try:
            pdf_size_bytes = pdf_path.stat().st_size if pdf_path.exists() else None
        except OSError:
            pdf_size_bytes = None

        document_text, pages_extracted = _read_pdf_text(pdf_path)

        # 2. Resolver provider (vía registry, salvo client inyectado)
        provider = _resolve_provider(resolved_model, client)
        provider_id = provider.provider_id

        if not provider.is_available():
            msg = (
                f"Provider '{provider.provider_id}' no está disponible "
                f"(faltan credenciales o config en este entorno)."
            )
            raise ProviderNotAvailableError(msg)

        # 3. Construir request y delegar al provider
        # case_id: filename sin extensión. Identifica el caso en Langfuse
        # y en telemetría. Si el path no se puede expresar (caso edge),
        # cae a None y el provider usa "unknown_case" como tag.
        case_id_for_trace: str | None
        try:
            case_id_for_trace = pdf_path.stem or None
        except Exception:
            case_id_for_trace = None

        req = ExtractionRequest(
            document_text=document_text,
            prompt=resolved_prompt,
            model_id=resolved_model,
            max_tokens=resolved_max_tokens,
            max_retries=resolved_max_retries,
            initial_backoff=resolved_initial_backoff,
            max_backoff=resolved_max_backoff,
            timeout_seconds=resolved_timeout,
            case_id=case_id_for_trace,
        )

        try:
            response = provider.extract(req)
        except AnthropicExtractionError as exc:
            # Re-raise como ExtractionError para mantener el contrato público.
            raise ExtractionError(str(exc)) from exc

        retry_count = response.retry_count
        if response.input_tokens is not None and response.output_tokens is not None:
            token_usage = {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            }

        # 4. Validación Pydantic
        try:
            summary = ObstetricSummary.model_validate(response.parsed_output)
        except ValidationError as exc:
            msg = f"El output del modelo no cumple el schema de ObstetricSummary: {exc}"
            raise ExtractionError(msg) from exc

        success = True
        return summary
    except Exception as exc:
        error_type = type(exc).__name__
        raise
    finally:
        latency_ms = int((time.perf_counter() - started) * 1000)
        telemetry.emit(
            {
                "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "operation_id": operation_id,
                "pdf_path": str(pdf_path),
                "pdf_size_bytes": pdf_size_bytes,
                "pages_extracted": pages_extracted,
                "provider_id": provider_id,
                "model_used": resolved_model,
                "prompt_version": resolved_prompt.version,
                "latency_ms": latency_ms,
                "retry_count": retry_count,
                "success": success,
                "error_type": error_type,
                "token_usage": token_usage,
            }
        )


# =========================================================================
# Compat shims — mantienen API que test_hardening.py importa directamente.
# =========================================================================

# Re-exporta los internals que los tests existentes consumen. Esto permite
# refactorizar la implementación sin romper imports de tests.
from clinical_extractor.providers.anthropic_provider import (  # noqa: E402
    _backoff_delay,
)


def _call_model_with_retry(
    *,
    client: anthropic.Anthropic,
    model: str,
    max_tokens: int,
    prompt: VersionedPrompt,
    document_text: str,
    max_retries: int,
    initial_backoff: float,
    max_backoff: float,
    sleep_fn: Any = time.sleep,
) -> tuple[dict[str, Any], dict[str, int] | None, int]:
    """Compat shim — delega al provider Anthropic con el client inyectado.

    Usado por tests existentes (test_hardening.py). Mantiene la firma vieja.
    """
    from clinical_extractor.providers.anthropic_provider import _call_with_retry

    req = ExtractionRequest(
        document_text=document_text,
        prompt=prompt,
        model_id=model,
        max_tokens=max_tokens,
        max_retries=max_retries,
        initial_backoff=initial_backoff,
        max_backoff=max_backoff,
    )
    try:
        return _call_with_retry(client=client, request=req, sleep_fn=sleep_fn)
    except AnthropicExtractionError as exc:
        raise ExtractionError(str(exc)) from exc


def _build_extraction_tool() -> Any:
    """Compat shim — re-exporta del provider."""
    from clinical_extractor.providers.anthropic_provider import (
        _build_extraction_tool as _bet,
    )

    return _bet()


__all__ = [
    "DEFAULT_INITIAL_BACKOFF_SECONDS",
    "DEFAULT_MAX_BACKOFF_SECONDS",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_MODEL",
    "DEFAULT_TIMEOUT_SECONDS",
    "ExtractionError",
    "_backoff_delay",
    "_build_extraction_tool",
    "_call_model_with_retry",
    "_read_pdf_text",
    "extract_from_pdf",
]
