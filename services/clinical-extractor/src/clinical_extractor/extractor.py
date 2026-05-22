"""Lógica core del clinical-extractor: PDF → ObstetricSummary.

Production hardening (R0 — Bloque 3):

- **Retry con backoff exponencial** sobre llamadas a Anthropic. Reintenta
  solo en errores transitorios (red, 429 rate limit, 5xx). NO reintenta
  en errores del cliente (400/401/403/422). Configurable vía argumentos
  o variables de entorno.
- **Timeout total por llamada** propagado al cliente Anthropic (default 60s).
- **Telemetría JSON-line** por extracción — operation_id, latencia, retry
  count, token usage, modelo, prompt version. NUNCA contenido del PDF ni PHI.

Decisión: implementación custom (sin tenacity) para minimizar dependencias
y mantener visibilidad completa del comportamiento de retry. La lógica es
~30 líneas y testeable sin trucos.
"""

from __future__ import annotations

import os
import random
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

import anthropic
import pypdf
from pydantic import ValidationError

from clinical_extractor import telemetry
from clinical_extractor.prompts import VersionedPrompt, get_active_prompt
from clinical_extractor.schemas import ObstetricSummary

if TYPE_CHECKING:
    from pathlib import Path

    from anthropic.types import MessageParam, ToolChoiceToolParam, ToolParam

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT_SECONDS = 60.0

# Retry policy defaults — overridables vía argumentos o env vars.
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_BACKOFF_SECONDS = 1.0
DEFAULT_MAX_BACKOFF_SECONDS = 16.0

TOOL_NAME = "record_obstetric_summary"

# Excepciones de Anthropic que SÍ disparan retry (transitorias).
_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)

# Excepciones que NUNCA dispararan retry (errores del cliente).
# Listadas explícitamente para que un cambio en anthropic-sdk no haga
# que reintentemos un 401 silenciosamente.
_NON_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    anthropic.BadRequestError,
    anthropic.AuthenticationError,
    anthropic.PermissionDeniedError,
    anthropic.NotFoundError,
    anthropic.UnprocessableEntityError,
)


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


def _build_extraction_tool() -> ToolParam:
    """Construye el tool spec para Anthropic basado en el schema de ObstetricSummary."""
    schema = ObstetricSummary.model_json_schema()
    tool: ToolParam = {
        "name": TOOL_NAME,
        "description": (
            "Registra el resumen estructurado de la historia clínica obstétrica "
            "extraído del documento. Llamar exactamente una vez."
        ),
        "input_schema": cast("Any", schema),
    }
    return tool


def _backoff_delay(attempt: int, initial: float, maximum: float) -> float:
    """Backoff exponencial con jitter ±20% para evitar thundering herd.

    attempt=0 → initial. attempt=1 → 2*initial. etc. Capa a `maximum`.
    """
    base = min(initial * (2**attempt), maximum)
    jitter = base * 0.2 * (random.random() * 2 - 1)  # noqa: S311 — no security context
    return max(0.0, base + jitter)


def _call_model_once(
    *,
    client: anthropic.Anthropic,
    model: str,
    max_tokens: int,
    prompt: VersionedPrompt,
    document_text: str,
) -> tuple[dict[str, Any], dict[str, int] | None]:
    """Una invocación al modelo. Devuelve (payload, token_usage)."""
    tool = _build_extraction_tool()
    user_message = prompt.user_template.format(document_text=document_text)
    tool_choice: ToolChoiceToolParam = {"type": "tool", "name": TOOL_NAME}
    messages: list[MessageParam] = [{"role": "user", "content": user_message}]

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=prompt.system,
        tools=[tool],
        tool_choice=tool_choice,
        messages=messages,
    )

    token_usage: dict[str, int] | None = None
    usage_obj = getattr(response, "usage", None)
    if usage_obj is not None:
        token_usage = {
            "input_tokens": int(getattr(usage_obj, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(usage_obj, "output_tokens", 0) or 0),
        }

    for block in response.content:
        if block.type == "tool_use" and block.name == TOOL_NAME:
            payload = block.input
            if not isinstance(payload, dict):
                msg = f"tool_use.input no es dict, es {type(payload).__name__}"
                raise ExtractionError(msg)
            return payload, token_usage

    msg = (
        "El modelo no devolvió un bloque tool_use con el nombre esperado. "
        f"stop_reason={response.stop_reason}, "
        f"content_types={[b.type for b in response.content]}"
    )
    raise ExtractionError(msg)


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
    sleep_fn=time.sleep,
) -> tuple[dict[str, Any], dict[str, int] | None, int]:
    """Wrapper con retry. Devuelve (payload, token_usage, retry_count).

    `sleep_fn` es inyectable para tests (evita esperas reales).
    """
    last_exc: BaseException | None = None
    for attempt in range(max_retries + 1):
        try:
            payload, usage = _call_model_once(
                client=client,
                model=model,
                max_tokens=max_tokens,
                prompt=prompt,
                document_text=document_text,
            )
            return payload, usage, attempt
        except _NON_RETRYABLE_EXCEPTIONS:
            # Errores del cliente — no tiene sentido reintentar.
            raise
        except _RETRYABLE_EXCEPTIONS as exc:
            last_exc = exc
            if attempt >= max_retries:
                break
            delay = _backoff_delay(attempt, initial_backoff, max_backoff)
            sleep_fn(delay)
            continue

    # Reintentos agotados.
    msg = (
        f"Reintentos agotados ({max_retries}) llamando al modelo. "
        f"Última excepción: {type(last_exc).__name__}: {last_exc}"
    )
    raise ExtractionError(msg) from last_exc


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
    """Extrae un `ObstetricSummary` desde un PDF nativo de historia obstétrica.

    Args:
        pdf_path: Ruta al PDF.
        model: ID del modelo Claude. Default: env CLAUDE_MODEL o claude-sonnet-4-5-20250929.
        max_tokens: Máximo de tokens de salida. Default: env CLAUDE_MAX_TOKENS o 4096.
        client: Cliente Anthropic preconfigurado (útil para tests). Si None, se construye uno.
        prompt: Versión del prompt a usar. Si None, se usa la activa por default.
        max_retries: Reintentos en errores transitorios. Default: env CLAUDE_MAX_RETRIES o 3.
        initial_backoff: Espera inicial entre reintentos en segundos.
            Default: env CLAUDE_INITIAL_BACKOFF o 1.0.
        max_backoff: Tope del backoff exponencial en segundos.
            Default: env CLAUDE_MAX_BACKOFF o 16.0.
        timeout_seconds: Timeout total por request al modelo.
            Default: env CLAUDE_TIMEOUT_SECONDS o 60.0.

    Returns:
        ObstetricSummary validado.

    Raises:
        ExtractionError: si el PDF no se puede leer, si el modelo no responde
            como se espera, si los retries se agotan, o si el output falla
            validación Pydantic.

    Telemetría: emite un registro JSON-line al logger
    `clinical_extractor.telemetry` (configurar StreamHandler vía
    `telemetry.configure_stream_handler` para verlo).
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
    success = False

    try:
        # 1. Read PDF
        try:
            pdf_size_bytes = pdf_path.stat().st_size if pdf_path.exists() else None
        except OSError:
            pdf_size_bytes = None

        document_text, pages_extracted = _read_pdf_text(pdf_path)

        # 2. Construir client si no se inyectó
        if client is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                msg = "ANTHROPIC_API_KEY no está en el entorno. Crear .env desde .env.example."
                raise ExtractionError(msg)
            client = anthropic.Anthropic(api_key=api_key, timeout=resolved_timeout)

        # 3. Llamada al modelo con retry
        raw_output, token_usage, retry_count = _call_model_with_retry(
            client=client,
            model=resolved_model,
            max_tokens=resolved_max_tokens,
            prompt=resolved_prompt,
            document_text=document_text,
            max_retries=resolved_max_retries,
            initial_backoff=resolved_initial_backoff,
            max_backoff=resolved_max_backoff,
        )

        # 4. Validación Pydantic
        try:
            summary = ObstetricSummary.model_validate(raw_output)
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
                "model_used": resolved_model,
                "prompt_version": resolved_prompt.version,
                "latency_ms": latency_ms,
                "retry_count": retry_count,
                "success": success,
                "error_type": error_type,
                "token_usage": token_usage,
            }
        )
