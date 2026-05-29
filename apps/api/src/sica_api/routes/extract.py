"""POST /extract — multipart upload de PDF → ObstetricSummary JSON.

Diseño:
- El archivo se procesa en disco (tempfile) porque el clinical-extractor
  recibe `Path`, no bytes. El tempfile se elimina siempre, incluso en
  fallo, vía bloque finally.
- Validamos size ANTES de leer el body completo: read en chunks y abortamos
  si excedemos `max_file_size_bytes` para evitar OOM en uploads maliciosos.
- Validamos content-type Y magic bytes (`%PDF-`). Content-type es trivial
  de spoofear; los magic bytes son la verificación real.
- Errores 5xx generan `error_id` UUID para correlación, pero NUNCA exponen
  stack trace ni contenido del PDF. PHI no debe filtrarse a logs ni a la
  respuesta de error.
"""

from __future__ import annotations

import logging
import tempfile
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse

from sica_api.settings import Settings, get_settings
from sica_api.tracing import (
    finish_extract_trace,
    get_span_id_from_context,
    get_trace_id_from_context,
    start_extract_trace,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from typing import Any

logger = logging.getLogger("sica_api.extract")

router = APIRouter(tags=["extract"])

PDF_MAGIC = b"%PDF-"
_CHUNK_BYTES = 64 * 1024

# --------------------------------------------------------------------------- #
# Provider routing — ADR 0004 § Actualización 2026-05-27.
#
# El query param ?provider= selecciona el LLM provider que atiende el request.
# Los valores públicos (PUBLIC_PROVIDERS) son los IDs cortos que el cliente
# usa. Internamente mapeamos al ``provider_id`` real del registry (que puede
# ser más largo, e.g. ``vertex-medgemma``).
# --------------------------------------------------------------------------- #

DEFAULT_PROVIDER = "anthropic"

# Mapeo público → ID interno del registry. Cambiar aquí requiere ADR (rompe
# contrato del query param). Cambiar el ID interno NO basta — el registry
# debe seguir reconociéndolo.
PROVIDER_ALIASES: dict[str, str] = {
    "anthropic": "anthropic",
    "vertex": "vertex-medgemma",
}

VALID_PROVIDERS: frozenset[str] = frozenset(PROVIDER_ALIASES.keys())

# Import del redactor PHI del extractor (ADR-0009). Coupling explícito:
# ``apps/api`` depende de ``clinical_extractor`` en runtime (render.yaml lo
# instala); en entornos minimalistas sin el extractor, el handler tampoco
# corre porque ``/extract`` ya quedaría 503 por settings.extractor_available.
# Aun así degradamos gracefully con un fallback que solo limpia whitespace
# si el import falla — el sistema sigue respondiendo, sin PHI redaction.
try:
    from clinical_extractor.phi import redact_phi as _redact_phi

    _redact_phi_available = True
except ImportError:  # pragma: no cover — entorno minimalista
    _redact_phi = None
    _redact_phi_available = False


def _safe_provider_error_detail(exc: BaseException) -> str:
    """Sanitiza el mensaje de excepción del provider para el response HTTP.

    Pipeline (en orden):

    1. Aplica ``redact_phi`` sobre el string crudo (defensa: patterns inline
       de DNI peruano 8-dig, móvil 9-dig prefijo 9, email). Ver ADR-0009.
    2. Colapsa whitespace (newlines / tabs → single space).
    3. Trunca a 200 chars.

    NUNCA incluye traceback ni paths absolutos. Para mensajes vacíos devuelve
    un fallback genérico. Si ``clinical_extractor.phi`` no se pudo importar
    (entorno minimalista), el paso 1 se saltea — el sistema sigue funcionando
    pero sin redaction de PHI; el deployment de producción tiene el extractor
    instalado, por lo que el path 1 corre.
    """
    raw = str(exc).strip()
    if not raw:
        return "El provider no está disponible en este entorno."
    # Paso 1: redact PHI inline (DNI / teléfono / email). redact_phi sobre str
    # aplica los patterns y devuelve un string nuevo. Es idempotente y puro.
    sanitized = _redact_phi(raw) if _redact_phi_available and _redact_phi is not None else raw
    # Paso 2: colapsar whitespace para no romper el JSON con saltos de línea.
    cleaned = " ".join(sanitized.split())
    # Paso 3: truncar.
    return cleaned[:200]


# --------------------------------------------------------------------------- #
# Adapter para inyectar el extractor en tests sin tocar la red.
# La función real se importa lazy en _default_extractor para que la API
# pueda iniciarse incluso si clinical_extractor no está instalado (ej. en
# un container minimalista que sólo sirve /health y /models).
# --------------------------------------------------------------------------- #


def _default_extractor(
    pdf_path: Path,
    *,
    api_key: str,
    parent_trace_id: str | None = None,
    parent_span_id: str | None = None,
    case_id: str | None = None,
    provider_id: str | None = None,
    metadata_out: dict[str, Any] | None = None,
) -> dict[str, Any]:
    import os

    os.environ["ANTHROPIC_API_KEY"] = api_key

    from clinical_extractor.extractor import (
        ExtractionError,
        extract_from_pdf,
    )

    try:
        summary = extract_from_pdf(
            pdf_path,
            parent_trace_id=parent_trace_id,
            parent_span_id=parent_span_id,
            case_id=case_id,
            provider_id=provider_id,
            metadata_out=metadata_out,
        )
    except ExtractionError:
        raise
    # model_dump returns Any from a Pydantic model, but we know it's a dict[str, Any].
    dumped: dict[str, Any] = summary.model_dump(mode="json")
    return dumped


def _build_response_metadata(
    *,
    extraction_metadata: dict[str, Any],
    request_id: str,
    parent_trace_id: str | None,
    requested_provider: str,
    internal_provider_id: str,
    latency_ms_fallback: float,
) -> dict[str, Any]:
    """Construye el bloque ``metadata`` del response 200 de /extract.

    Args:
        extraction_metadata: Dict llenado por ``extract_from_pdf`` vía el
            kwarg ``metadata_out``. Puede estar vacío si el extractor
            inyectado en tests no lo llena — en ese caso emitimos fallback.
        request_id: X-Request-ID del request actual.
        parent_trace_id: Trace ID Langfuse (si tracing activo). None si no.
        requested_provider: Alias público del provider (``anthropic``,
            ``vertex``). Lo que el cliente envió en query param.
        internal_provider_id: ID del registry. Lo eco como provider_id
            cuando el extractor no llenó metadata.
        latency_ms_fallback: Latencia medida por el handler — fallback
            cuando el extractor no llenó la suya (test seam).

    Returns:
        Dict serializable JSON con todos los campos de
        ``ExtractionMetadata``. Pasar este dict por
        ``ExtractionMetadata.model_validate(...)`` debe ser idempotente.
    """
    # ``extraction_metadata`` puede venir vacío si el extractor inyectado
    # no llenó ``metadata_out``. Calzamos defaults razonables que no
    # mientan: model_used falla a unknown, prompt_version a unknown,
    # tokens a None.
    # ``provider_id`` canónico es el del registry. El alias público
    # (anthropic/vertex) se reflejaría en otra capa si hace falta; aquí
    # no lo agregamos para mantener ``extra="forbid"`` del schema.
    del requested_provider  # documenta no-uso intencional para linters

    latency_raw = extraction_metadata.get("latency_ms")
    latency_value: float
    if latency_raw is not None:
        latency_value = float(latency_raw)
    else:
        latency_value = latency_ms_fallback

    out: dict[str, Any] = {
        "operation_id": extraction_metadata.get("operation_id") or str(uuid.uuid4()),
        "provider_id": extraction_metadata.get("provider_id") or internal_provider_id,
        "model_used": extraction_metadata.get("model_used") or "unknown",
        "prompt_version": extraction_metadata.get("prompt_version") or "unknown",
        "prompt_hash": extraction_metadata.get("prompt_hash"),
        "input_tokens": extraction_metadata.get("input_tokens"),
        "output_tokens": extraction_metadata.get("output_tokens"),
        "cost_usd": extraction_metadata.get("cost_usd"),
        "latency_ms": int(latency_value),
        "retry_count": extraction_metadata.get("retry_count", 0),
        "success": extraction_metadata.get("success", True),
        "error_type": extraction_metadata.get("error_type"),
        "trace_id": parent_trace_id,
        "request_id": request_id,
    }
    return out


# Hook reemplazable en tests vía dependency_overrides
def get_extractor() -> Callable[..., Awaitable[dict[str, Any]] | dict[str, Any]]:
    return _default_extractor


# --------------------------------------------------------------------------- #
# Endpoint
# --------------------------------------------------------------------------- #


@router.post(
    "/extract",
    summary="Extrae un ObstetricSummary estructurado desde un PDF clínico.",
    responses={
        400: {"description": "Archivo inválido (no es PDF) o provider inválido."},
        413: {"description": "Archivo excede el tamaño máximo permitido."},
        422: {"description": "Body multipart inválido o falta el campo 'file'."},
        500: {"description": "Error interno — el cliente recibe un error_id."},
        503: {
            "description": (
                "Extractor o provider no disponible (falta ANTHROPIC_API_KEY, "
                "GCP creds para vertex, etc.)."
            )
        },
    },
)
async def extract(
    request: Request,
    file: UploadFile = File(..., description="PDF de historia clínica obstétrica."),
    provider: str = Query(
        default=DEFAULT_PROVIDER,
        description=(
            "ID del provider LLM a usar. Valores válidos: 'anthropic' (default), "
            "'vertex'. 'vertex' retorna 503 hasta que GCP MedGemma esté configurado "
            "(issue #12). Ver ADR 0004 § Actualización 2026-05-27."
        ),
    ),
    settings: Settings = Depends(get_settings),
    extractor: Callable[..., Any] = Depends(get_extractor),
) -> JSONResponse:
    """Procesa un PDF y devuelve un ObstetricSummary en JSON.

    Headers que el caller recibe en la respuesta:
      - X-Request-ID: UUID que identifica la operación end-to-end.

    El output NO es diagnóstico clínico. Es asistivo. Debe ser revisado
    por un médico antes de cualquier uso clínico.
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    response_headers = {"X-Request-ID": request_id}

    # ---- 0. Provider routing — validación temprana ANTES de leer el PDF
    # (no desperdiciar I/O si el query param es inválido). Acepta string
    # vacío y mapea al default — comportamiento estándar de FastAPI Query
    # también lo daría, pero hacerlo explícito documenta la decisión.
    requested_provider = (provider or DEFAULT_PROVIDER).lower()
    if requested_provider not in VALID_PROVIDERS:
        # Defensa PHI (ADR-0009): el cliente puede enviar cualquier string
        # como query param; sanitizamos antes de eco en el response.
        safe_provider_echo = (
            _redact_phi(provider)
            if _redact_phi_available and _redact_phi is not None
            else provider
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            headers=response_headers,
            content={
                "error": "invalid_provider",
                "detail": (
                    f"Provider '{safe_provider_echo}' no es válido. "
                    f"Valores aceptados: {sorted(VALID_PROVIDERS)}."
                ),
                "provider": safe_provider_echo,
                "request_id": request_id,
            },
        )
    # Internal ID: el registry del extractor conoce 'anthropic' y 'vertex-medgemma'.
    internal_provider_id = PROVIDER_ALIASES[requested_provider]

    # ---- 1. Extractor disponible
    if not settings.extractor_available:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            headers=response_headers,
            content={
                "error": "extractor_unavailable",
                "detail": (
                    "El extractor no está configurado: falta ANTHROPIC_API_KEY. "
                    "Configurar .env y reiniciar el servicio."
                ),
                "request_id": request_id,
            },
        )

    # ---- 2. Content-type sanity check (no autoritativo, sólo señal temprana)
    content_type = (file.content_type or "").lower()
    filename = file.filename or "<unnamed>"
    # case_id estable para observability: filename del upload sin extensión,
    # ej "synthetic_case_01.pdf" → "synthetic_case_01". Si no hay filename
    # útil (UploadFile sin nombre), cae a "uploaded_pdf". Esto evita que el
    # dashboard de Langfuse muestre el nombre del tempfile (sica-api-XXXX),
    # que es lo que ocurría antes — ver ADR 0007 § Limitación conocida.
    case_id_from_upload = Path(filename).stem if filename and filename != "<unnamed>" else ""
    case_id_for_extractor = case_id_from_upload or "uploaded_pdf"
    if content_type and "pdf" not in content_type:
        # Defensa PHI (ADR-0009): content_type proviene del cliente; sanitizar
        # antes de eco. En la práctica nunca trae PHI, pero defense in depth.
        safe_content_type_echo = (
            _redact_phi(content_type)
            if _redact_phi_available and _redact_phi is not None
            else content_type
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            headers=response_headers,
            content={
                "error": "not_a_pdf",
                "detail": (
                    f"El archivo declara content-type '{safe_content_type_echo}', "
                    "se esperaba application/pdf."
                ),
                "request_id": request_id,
            },
        )

    # ---- 3. Read body en chunks con guard de tamaño + magic-bytes check
    max_bytes = settings.max_file_size_bytes
    received = bytearray()
    try:
        while True:
            chunk = await file.read(_CHUNK_BYTES)
            if not chunk:
                break
            received.extend(chunk)
            if len(received) > max_bytes:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    headers=response_headers,
                    content={
                        "error": "file_too_large",
                        "detail": (
                            f"El archivo excede el límite configurado de "
                            f"{settings.max_file_size_mb} MB."
                        ),
                        "request_id": request_id,
                    },
                )
    finally:
        await file.close()

    if len(received) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            headers=response_headers,
            content={
                "error": "empty_file",
                "detail": "El archivo subido está vacío.",
                "request_id": request_id,
            },
        )

    if not bytes(received[: len(PDF_MAGIC)]).startswith(PDF_MAGIC):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            headers=response_headers,
            content={
                "error": "not_a_pdf",
                "detail": (
                    "El contenido no comienza con magic bytes %PDF-. "
                    "El archivo no parece un PDF válido."
                ),
                "request_id": request_id,
            },
        )

    # ---- 4. Iniciar trace padre (no-op si Langfuse deshabilitado)
    # Se hace ANTES del extractor para que el trace_id viaje como parent.
    # ``start_extract_trace`` jamás levanta — graceful degradation absoluta.
    # Pasamos el ``provider`` (alias público) en metadata para auditoría.
    trace_context = start_extract_trace(
        request_id=request_id,
        pdf_filename=filename,
        pdf_size_bytes=len(received),
        user_metadata={"provider": requested_provider},
    )
    parent_trace_id = get_trace_id_from_context(trace_context)
    parent_span_id = get_span_id_from_context(trace_context)
    extract_started = time.perf_counter()

    # ---- 5. Persist temp PDF (extractor espera Path)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="sica-api-", suffix=".pdf", delete=False
        ) as tmp:
            tmp.write(received)
            tmp_path = Path(tmp.name)

        # ---- 6. Ejecutar extractor (con trace context propagado)
        logger.info(
            "extract start",
            extra={
                "request_id": request_id,
                "provider": requested_provider,
                "internal_provider_id": internal_provider_id,
                "uploaded_filename": filename,
                "size_bytes": len(received),
            },
        )
        try:
            assert settings.anthropic_api_key is not None  # narrowing for mypy
            extraction_metadata: dict[str, Any] = {}
            payload = extractor(
                tmp_path,
                api_key=settings.anthropic_api_key,
                parent_trace_id=parent_trace_id,
                parent_span_id=parent_span_id,
                case_id=case_id_for_extractor,
                provider_id=internal_provider_id,
                metadata_out=extraction_metadata,
            )
        except Exception as exc:
            # ---- 6a. Errores específicos de provider → 503 (no 500).
            # ``ProviderNotAvailableError`` (vertex sin GCP creds), o
            # ``NotImplementedError`` que levanta VertexMedGemmaProvider.extract
            # (stub) son ambos "el provider seleccionado no atiende ahora" —
            # el cliente puede orquestar reintento con otro provider.
            # Detección por nombre para evitar acoplar apps/api al extractor
            # tipo-import (mantenemos el extractor como optional dependency).
            exc_type = type(exc).__name__
            is_provider_unavailable = (
                exc_type == "ProviderNotAvailableError"
                or isinstance(exc, NotImplementedError)
            )
            error_id = str(uuid.uuid4())
            latency_ms = (time.perf_counter() - extract_started) * 1000
            logger.exception(
                "extract failed",
                extra={
                    "request_id": request_id,
                    "error_id": error_id,
                    "provider": requested_provider,
                    "size_bytes": len(received),
                    "exception_type": exc_type,
                },
            )
            # Cierra el trace padre con outcome de error. No-op si tracing
            # deshabilitado. Nunca levanta — el cliente recibe el error igual.
            # ADR-0009: el ``error`` string va a Langfuse Cloud como metadata.
            # Pasa por ``_safe_provider_error_detail`` para redactar PHI inline
            # (DNI / teléfono / email) que el provider haya puesto en la excepción.
            sanitized_error_for_trace = (
                f"{exc_type}: {_safe_provider_error_detail(exc)}"
            )
            finish_extract_trace(
                trace_context,
                success=False,
                latency_ms=latency_ms,
                error=sanitized_error_for_trace,
                output_summary={
                    "error_id": error_id,
                    "uploaded_filename": filename,
                    "size_bytes": len(received),
                    "provider": requested_provider,
                },
            )
            if is_provider_unavailable:
                # 503 — el provider está mapeado en el registry pero no es
                # operativo (env vars faltantes, stub no implementado).
                # Sin stack trace ni datos del PDF en el detail.
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    headers={**response_headers, "X-Error-ID": error_id},
                    content={
                        "error": "provider_unavailable",
                        "detail": (
                            f"Provider '{requested_provider}' no disponible: "
                            f"{_safe_provider_error_detail(exc)}"
                        ),
                        "provider": requested_provider,
                        "error_type": exc_type,
                        "request_id": request_id,
                        "error_id": error_id,
                    },
                )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                headers={**response_headers, "X-Error-ID": error_id},
                content={
                    "error": "extraction_failed",
                    "detail": (
                        "El extractor falló procesando el documento. "
                        "Citar el error_id al pedir soporte."
                    ),
                    "provider": requested_provider,
                    "request_id": request_id,
                    "error_id": error_id,
                },
            )

        # ---- 7. Success
        # NOTE: avoid `filename` as an extra key — it's a reserved
        # LogRecord attribute and the logging module raises KeyError.
        latency_ms = (time.perf_counter() - extract_started) * 1000
        logger.info(
            "extract ok",
            extra={
                "request_id": request_id,
                "uploaded_filename": filename,
                "size_bytes": len(received),
            },
        )
        # Resumen seguro para Langfuse — NUNCA pasar el payload completo
        # como output del span padre. El generation child del extractor ya
        # tiene el output_json detallado; acá sólo metadata operacional.
        # Esto es importante para limitar superficie de PHI cuando exista.
        output_summary: dict[str, Any] = {
            "confidence_score": payload.get("confidence_score"),
            "num_evidence_spans": len(payload.get("evidence_spans") or []),
            "num_active_problems": len(payload.get("active_problems") or []),
            "num_lab_results": len(payload.get("lab_results") or []),
            "uploaded_filename": filename,
            "size_bytes": len(received),
        }
        finish_extract_trace(
            trace_context,
            success=True,
            latency_ms=latency_ms,
            output_summary=output_summary,
        )

        # Construir el bloque ``metadata`` para el response. Es aditivo:
        # los campos del ObstetricSummary siguen al top-level del payload,
        # sumamos un campo ``metadata`` con la trazabilidad operacional.
        # Si el extractor (fake en tests, real en prod) llenó
        # ``extraction_metadata``, lo usamos; si no, exponemos un fallback
        # mínimo derivado del request actual.
        metadata_payload = _build_response_metadata(
            extraction_metadata=extraction_metadata,
            request_id=request_id,
            parent_trace_id=parent_trace_id,
            requested_provider=requested_provider,
            internal_provider_id=internal_provider_id,
            latency_ms_fallback=latency_ms,
        )
        payload["metadata"] = metadata_payload
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            headers=response_headers,
            content=payload,
        )
    finally:
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                logger.warning("could not delete temp file", extra={"path": str(tmp_path)})
