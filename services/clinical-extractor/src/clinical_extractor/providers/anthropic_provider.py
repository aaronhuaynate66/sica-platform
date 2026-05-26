"""Provider Anthropic Claude — implementación production-ready del LLMProvider.

Encapsula la integración con anthropic-python-sdk:
- Construcción del cliente con timeout configurable.
- Llamada al modelo con tool_use (schema ObstetricSummary).
- Retry con backoff exponencial sobre errores transitorios.
- Mapeo de excepciones SDK → ExtractionError/ProviderNotAvailableError.

Vetado para PHI real por ADR 0003 — uso permitido para desarrollo y datos
sintéticos/desidentificados según ``docs/security/data-handling.md`` § 7.
"""

from __future__ import annotations

import os
import random
import time
from typing import TYPE_CHECKING, Any, cast

import anthropic

from clinical_extractor.providers.base import (
    ExtractionRequest,
    ExtractionResponse,
    LLMProvider,
    ProviderNotAvailableError,
)
from clinical_extractor.schemas import ObstetricSummary

if TYPE_CHECKING:
    from anthropic.types import MessageParam, ToolChoiceToolParam, ToolParam

    from clinical_extractor.prompts import VersionedPrompt


def _safe_trace(**kwargs: Any) -> None:
    """Wrapper defensivo: aún si tracing.py fallara al importar, no rompe extract.

    Este wrapper existe porque ``trace_extraction`` ya tiene try/except
    interno, pero el ``import`` mismo podría romperse si el módulo de
    settings tiene un bug. Doble cinturón = el extractor no puede caerse
    por la observability.
    """
    try:
        from clinical_extractor.tracing import trace_extraction

        trace_extraction(**kwargs)
    except Exception:
        # Logger ya advirtió desde tracing.py si fue ese path; si fue
        # ImportError o algo más exótico, swalloweamos silencioso.
        # Re-raise rompería la regla "tracing no debe romper extract".
        return

TOOL_NAME = "record_obstetric_summary"

# Excepciones que SÍ disparan retry (transitorias).
_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)

# Excepciones que NUNCA disparan retry (errores del cliente).
# Listadas explícitamente para que un cambio en anthropic-sdk no haga que
# reintentemos un 401 silenciosamente.
_NON_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    anthropic.BadRequestError,
    anthropic.AuthenticationError,
    anthropic.PermissionDeniedError,
    anthropic.NotFoundError,
    anthropic.UnprocessableEntityError,
)


class AnthropicExtractionError(RuntimeError):
    """Falla en la pipeline de extracción Anthropic (re-raised como ExtractionError arriba)."""


class AnthropicProvider(LLMProvider):
    """Provider Anthropic — Claude Sonnet/Opus/Haiku.

    Args:
        client: Cliente Anthropic preconfigurado (útil para tests). Si None,
            se construye lazy en ``extract`` usando ``ANTHROPIC_API_KEY``.
    """

    _PROVIDER_ID = "anthropic"
    _SUPPORTED_MODELS = (
        "claude-sonnet-4-5-20250929",
        "claude-opus-4-7",
        "claude-haiku-4-5-20251001",
    )

    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        self._injected_client = client

    @property
    def provider_id(self) -> str:
        return self._PROVIDER_ID

    @property
    def supported_models(self) -> list[str]:
        return list(self._SUPPORTED_MODELS)

    def is_available(self) -> bool:
        if self._injected_client is not None:
            return True
        return bool(os.getenv("ANTHROPIC_API_KEY"))

    def extract(self, request: ExtractionRequest) -> ExtractionResponse:
        if request.model_id not in self._SUPPORTED_MODELS:
            msg = (
                f"AnthropicProvider no soporta el modelo '{request.model_id}'. "
                f"Soportados: {list(self._SUPPORTED_MODELS)}"
            )
            raise ValueError(msg)

        client = self._resolve_client(timeout_seconds=request.timeout_seconds)
        started = time.perf_counter()
        case_id_for_trace = request.case_id or "unknown_case"

        try:
            payload, usage, retries = _call_with_retry(
                client=client,
                request=request,
            )
        except Exception as exc:
            # Tracing del error ANTES de re-raise — sin esto la falla queda
            # invisible en Langfuse aunque sí en stdout/telemetry.
            latency_ms = int((time.perf_counter() - started) * 1000)
            _safe_trace(
                case_id=case_id_for_trace,
                model=request.model_id,
                provider_id=self._PROVIDER_ID,
                input_tokens=None,
                output_tokens=None,
                latency_ms=latency_ms,
                output_json=None,
                error=f"{type(exc).__name__}: {exc}",
                metadata={"retries": "unknown_at_failure"},
                parent_trace_id=request.parent_trace_id,
                parent_span_id=request.parent_span_id,
            )
            raise

        latency_ms = int((time.perf_counter() - started) * 1000)

        # Trace exitoso. Por diseño no debe romper la respuesta — _safe_trace
        # envuelve cualquier excepción de Langfuse.
        _safe_trace(
            case_id=case_id_for_trace,
            model=request.model_id,
            provider_id=self._PROVIDER_ID,
            input_tokens=usage["input_tokens"] if usage else None,
            output_tokens=usage["output_tokens"] if usage else None,
            latency_ms=latency_ms,
            output_json=payload,
            error=None,
            metadata={"retries": retries},
            parent_trace_id=request.parent_trace_id,
            parent_span_id=request.parent_span_id,
        )

        return ExtractionResponse(
            parsed_output=payload,
            input_tokens=usage["input_tokens"] if usage else None,
            output_tokens=usage["output_tokens"] if usage else None,
            latency_ms=latency_ms,
            model_used=request.model_id,
            finish_reason="tool_use",
            retry_count=retries,
        )

    def _resolve_client(self, *, timeout_seconds: float) -> anthropic.Anthropic:
        if self._injected_client is not None:
            return self._injected_client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            msg = (
                "AnthropicProvider no disponible: ANTHROPIC_API_KEY no está en "
                "el entorno. Crear .env desde .env.example."
            )
            raise ProviderNotAvailableError(msg)
        return anthropic.Anthropic(api_key=api_key, timeout=timeout_seconds)


# =========================================================================
# Internals — retry, single call, tool spec
# =========================================================================


def _build_extraction_tool() -> ToolParam:
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
    base = min(initial * (2**attempt), maximum)
    jitter = base * 0.2 * (random.random() * 2 - 1)
    return float(max(0.0, base + jitter))


def _call_once(
    *,
    client: anthropic.Anthropic,
    model: str,
    max_tokens: int,
    prompt: VersionedPrompt,
    document_text: str,
) -> tuple[dict[str, Any], dict[str, int] | None]:
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
                raise AnthropicExtractionError(msg)
            return payload, token_usage

    msg = (
        "El modelo no devolvió un bloque tool_use con el nombre esperado. "
        f"stop_reason={response.stop_reason}, "
        f"content_types={[b.type for b in response.content]}"
    )
    raise AnthropicExtractionError(msg)


def _call_with_retry(
    *,
    client: anthropic.Anthropic,
    request: ExtractionRequest,
    sleep_fn: Any = time.sleep,
) -> tuple[dict[str, Any], dict[str, int] | None, int]:
    """Loop de retry. Devuelve (payload, token_usage, retry_count)."""
    last_exc: BaseException | None = None
    for attempt in range(request.max_retries + 1):
        try:
            payload, usage = _call_once(
                client=client,
                model=request.model_id,
                max_tokens=request.max_tokens,
                prompt=request.prompt,
                document_text=request.document_text,
            )
            return payload, usage, attempt
        except _NON_RETRYABLE_EXCEPTIONS:
            raise
        except _RETRYABLE_EXCEPTIONS as exc:
            last_exc = exc
            if attempt >= request.max_retries:
                break
            delay = _backoff_delay(
                attempt, request.initial_backoff, request.max_backoff
            )
            sleep_fn(delay)
            continue

    msg = (
        f"Reintentos agotados ({request.max_retries}) llamando al modelo "
        f"{request.model_id}. Última excepción: {type(last_exc).__name__}: {last_exc}"
    )
    raise AnthropicExtractionError(msg) from last_exc
