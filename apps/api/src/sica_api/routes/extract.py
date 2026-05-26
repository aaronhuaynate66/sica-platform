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

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
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
        )
    except ExtractionError:
        raise
    # model_dump returns Any from a Pydantic model, but we know it's a dict[str, Any].
    dumped: dict[str, Any] = summary.model_dump(mode="json")
    return dumped


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
        400: {"description": "Archivo inválido (no es PDF)."},
        413: {"description": "Archivo excede el tamaño máximo permitido."},
        422: {"description": "Body multipart inválido o falta el campo 'file'."},
        500: {"description": "Error interno — el cliente recibe un error_id."},
        503: {"description": "Extractor no disponible (falta ANTHROPIC_API_KEY)."},
    },
)
async def extract(
    request: Request,
    file: UploadFile = File(..., description="PDF de historia clínica obstétrica."),
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
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            headers=response_headers,
            content={
                "error": "not_a_pdf",
                "detail": (
                    f"El archivo declara content-type '{content_type}', se esperaba application/pdf."
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
    trace_context = start_extract_trace(
        request_id=request_id,
        pdf_filename=filename,
        pdf_size_bytes=len(received),
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
        try:
            assert settings.anthropic_api_key is not None  # narrowing for mypy
            payload = extractor(
                tmp_path,
                api_key=settings.anthropic_api_key,
                parent_trace_id=parent_trace_id,
                parent_span_id=parent_span_id,
                case_id=case_id_for_extractor,
            )
        except Exception as exc:
            error_id = str(uuid.uuid4())
            latency_ms = (time.perf_counter() - extract_started) * 1000
            logger.exception(
                "extract failed",
                extra={
                    "request_id": request_id,
                    "error_id": error_id,
                    "size_bytes": len(received),
                    "exception_type": type(exc).__name__,
                },
            )
            # Cierra el trace padre con outcome de error. No-op si tracing
            # deshabilitado. Nunca levanta — el cliente recibe el 500 igual.
            finish_extract_trace(
                trace_context,
                success=False,
                latency_ms=latency_ms,
                error=f"{type(exc).__name__}: {exc}",
                output_summary={
                    "error_id": error_id,
                    "uploaded_filename": filename,
                    "size_bytes": len(received),
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
