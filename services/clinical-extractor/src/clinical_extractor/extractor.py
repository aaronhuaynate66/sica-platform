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


def _resolve_prompt(prompt_version: int | None) -> VersionedPrompt:
    """Resuelve el prompt activo, con override opcional por versión entera.

    - ``None`` → comportamiento legacy: ``prompts.get_active_prompt()`` (latest
      via registry).
    - ``int`` → carga la versión exacta de ``extract_obstetric`` del registry.
      Si no existe, propaga ``FileNotFoundError`` envuelto en ``ExtractionError``
      con detalle de versiones disponibles.

    Devuelve un ``VersionedPrompt`` (NamedTuple legacy) para mantener compat
    con el resto del pipeline que consume ``.system`` + ``.user_template``.
    """
    if prompt_version is None:
        return get_active_prompt()

    # Import diferido del registry (la API pública del prompts package no
    # reexpone la entrada con override entero; el wrapper legacy solo acepta
    # version string).
    from clinical_extractor.prompts import VersionedPrompt as _VP
    from clinical_extractor.prompts.registry import (
        get_active_prompt as registry_get_active,
    )
    from clinical_extractor.prompts.registry import (
        list_versions,
    )

    try:
        pv = registry_get_active("extract_obstetric", version_override=prompt_version)
    except FileNotFoundError as exc:
        available = list_versions("extract_obstetric")
        msg = (
            f"Prompt 'extract_obstetric' versión {prompt_version} no existe. "
            f"Versiones disponibles: {available}."
        )
        raise ExtractionError(msg) from exc

    # Mapear el shape nuevo (registry.PromptVersion) al legacy (NamedTuple).
    # version_string lleva forma "extract_obstetric_v1"; preservamos string
    # legacy ("0.1.0") para v1 para no romper telemetría existente, y usamos
    # version_string para v2+ cuando aparezcan.
    legacy_version_string = "0.1.0" if pv.version == 1 else pv.version_string
    return _VP(
        version=legacy_version_string,
        system=pv.system,
        user_template=pv.user_template,
    )


def _resolve_provider(
    model_id: str,
    client: anthropic.Anthropic | None,
    provider_id: str | None = None,
) -> LLMProvider:
    """Resuelve el provider para una extracción.

    Orden de precedencia:

    1. Si se inyecta ``client`` (tests/dependency injection), siempre se
       devuelve un ``AnthropicProvider`` ad-hoc con ese cliente —
       retrocompatibilidad con tests que inyectaban el cliente directamente.
    2. Si ``provider_id`` viene explícito (caller seleccionó provider, e.g.
       ``apps/api`` con query param), se busca por ID en el registry. Esto
       permite enrutamiento explícito independiente del modelo.
    3. Si no, se resuelve por ``model_id`` (comportamiento histórico).

    Raises:
        ExtractionError: si el ``provider_id`` no existe en el registry o
            si ningún provider soporta ``model_id``.
    """
    if client is not None:
        return AnthropicProvider(client=client)

    if provider_id is not None:
        try:
            return DEFAULT_REGISTRY.get(provider_id)
        except ValueError as exc:
            # ValueError del registry → traducir a ExtractionError para el
            # contrato público.
            raise ExtractionError(str(exc)) from exc

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
    prompt_version: int | None = None,
    max_retries: int | None = None,
    initial_backoff: float | None = None,
    max_backoff: float | None = None,
    timeout_seconds: float | None = None,
    parent_trace_id: str | None = None,
    parent_span_id: str | None = None,
    case_id: str | None = None,
    provider_id: str | None = None,
    metadata_out: dict[str, Any] | None = None,
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
            Tiene precedencia sobre ``prompt_version`` cuando ambos están presentes.
        prompt_version: Número entero de versión específica del prompt
            ``extract_obstetric`` (e.g. ``1``). Resuelve vía
            ``clinical_extractor.prompts.registry.get_active_prompt`` con
            ``version_override``. Útil para reproducir corridas antiguas
            o forzar una versión específica desde CLI. Si la versión no
            existe, se levanta ``ExtractionError`` con detalle. Default
            None → usa la última versión disponible (Fase 1: v1).
        max_retries: Reintentos en errores transitorios. Default: env o 3.
        initial_backoff: Espera inicial entre reintentos en segundos.
        max_backoff: Tope del backoff exponencial en segundos.
        timeout_seconds: Timeout total por request al modelo.
        parent_trace_id: Trace ID del span padre en Langfuse — si está
            presente, la generation cuelga como child. Ver ADR 0007.
        parent_span_id: Span ID del padre, mejora la anidación visual.
        case_id: Identificador estable del caso para observability.
            Override del default (que es ``pdf_path.stem``). Útil cuando
            ``pdf_path`` es un tempfile (e.g. ``apps/api`` pasa aquí el
            filename original del upload). Si None, se deriva del path.
        provider_id: ID explícito del provider (``anthropic``,
            ``vertex-medgemma``, ...). Si se provee, el registry resuelve
            por ID y se ignora la resolución basada en ``model``. Si
            ``model`` también está ausente, el provider usa su primer
            ``supported_model`` (default). Útil para routing desde
            ``apps/api`` con query param.
        metadata_out: Dict opcional inyectado por el caller. Cuando se
            provee, la función lo llena (in-place) con metadata operacional
            de la extracción: ``operation_id``, ``provider_id``,
            ``model_used``, ``prompt_version``, ``prompt_hash``,
            ``input_tokens``, ``output_tokens``, ``cost_usd``,
            ``latency_ms``, ``retry_count``, ``success``, ``error_type``.
            Ningún campo lleva PHI. Si ``None`` (default), la función no
            expone metadata — comportamiento legacy intacto. Permite que
            ``apps/api`` exponga la metadata en el response sin duplicar
            la lógica del extractor.

    Returns:
        ObstetricSummary validado.

    Raises:
        ExtractionError: si el PDF no se puede leer, si el modelo no responde
            como se espera, si los retries se agotan, si el output falla
            validación Pydantic, o si no hay provider para ``model`` /
            ``provider_id``.
        ProviderNotAvailableError: si el provider seleccionado no está
            configurado (ej. ``ANTHROPIC_API_KEY`` ausente, GCP creds
            faltantes para vertex-medgemma).

    Telemetría: emite un registro JSON-line al logger
    ``clinical_extractor.telemetry`` con campos: timestamp, operation_id,
    provider_id, model_used, prompt_version, latency_ms, retry_count,
    token_usage, success, error_type.
    """
    resolved_model: str = model or os.getenv("CLAUDE_MODEL") or DEFAULT_MODEL
    resolved_max_tokens = max_tokens or int(
        os.getenv("CLAUDE_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))
    )
    resolved_prompt = prompt or _resolve_prompt(prompt_version)
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
    # ID efectivo del provider (lo que el registry resolvió). Diferente del
    # kwarg ``provider_id`` que es el input del caller.
    effective_provider_id: str | None = None
    success = False

    # Hash del prompt para auditoría. Se resuelve via registry — el prompt
    # legacy no tiene ``short_hash``, pero todos los prompts activos pasan
    # por el registry. Si la resolución falla (caso raro), queda None.
    prompt_hash_value: str | None = None
    try:
        from clinical_extractor.prompts.registry import (
            get_active_prompt as _registry_active,
        )

        # Si el caller pasó ``prompt_version``, intentamos resolver ese
        # hash; si pasó ``prompt`` precompilado o None, usamos el activo.
        if prompt is not None:
            # No tenemos el archivo origen del prompt inyectado — sin hash.
            prompt_hash_value = None
        elif prompt_version is not None:
            prompt_hash_value = _registry_active(
                "extract_obstetric", version_override=prompt_version
            ).short_hash
        else:
            prompt_hash_value = _registry_active("extract_obstetric").short_hash
    except Exception:
        # No bloquear extracción por falla resolviendo hash.
        prompt_hash_value = None

    try:
        # 1. Read PDF
        try:
            pdf_size_bytes = pdf_path.stat().st_size if pdf_path.exists() else None
        except OSError:
            pdf_size_bytes = None

        document_text, pages_extracted = _read_pdf_text(pdf_path)

        # 2. Resolver provider — precedencia: client inyectado >
        # provider_id explícito (apps/api con query param) > resolución por model.
        provider = _resolve_provider(resolved_model, client, provider_id=provider_id)
        effective_provider_id = provider.provider_id

        # Si el caller pidió un provider explícito sin model, usar el primer
        # supported_model del provider como default. Esto permite que el
        # caller diga "use vertex" sin tener que conocer el model_id concreto.
        if (
            provider_id is not None
            and not model
            and not os.getenv("CLAUDE_MODEL")
            and provider.supported_models
        ):
            resolved_model = provider.supported_models[0]

        if not provider.is_available():
            msg = (
                f"Provider '{provider.provider_id}' no está disponible "
                f"(faltan credenciales o config en este entorno)."
            )
            raise ProviderNotAvailableError(msg)

        # 3. Construir request y delegar al provider
        # case_id: 1) explícito del caller (apps/api propaga el filename
        # original del upload, NO el tempfile), 2) fallback a pdf_path.stem
        # (CLI / batch jobs locales donde el path SÍ es el filename real),
        # 3) None — el provider usa "unknown_case" como tag.
        # Identifica el caso en Langfuse + telemetría.
        case_id_for_trace: str | None
        if case_id:
            case_id_for_trace = case_id
        else:
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
            parent_trace_id=parent_trace_id,
            parent_span_id=parent_span_id,
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
                "provider_id": effective_provider_id,
                "model_used": resolved_model,
                "prompt_version": resolved_prompt.version,
                "latency_ms": latency_ms,
                "retry_count": retry_count,
                "success": success,
                "error_type": error_type,
                "token_usage": token_usage,
            }
        )

        # Llenado opcional de metadata_out para callers que lo solicitaron
        # (típicamente ``apps/api`` que lo expone en el response HTTP).
        # NUNCA pone PHI — solo IDs, conteos, modelo y costo.
        if metadata_out is not None:
            from clinical_extractor.pricing import calculate_cost_usd

            input_tokens = token_usage.get("input_tokens") if token_usage else None
            output_tokens = token_usage.get("output_tokens") if token_usage else None
            cost_usd: float | None
            if input_tokens is not None and output_tokens is not None:
                cost_usd = calculate_cost_usd(
                    resolved_model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            else:
                cost_usd = None

            metadata_out.update(
                {
                    "operation_id": operation_id,
                    "provider_id": effective_provider_id,
                    "model_used": resolved_model,
                    "prompt_version": resolved_prompt.version,
                    "prompt_hash": prompt_hash_value,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost_usd": cost_usd,
                    "latency_ms": latency_ms,
                    "retry_count": retry_count,
                    "success": success,
                    "error_type": error_type,
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
