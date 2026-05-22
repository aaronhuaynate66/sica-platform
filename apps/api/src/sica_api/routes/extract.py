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
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse

from sica_api.settings import Settings, get_settings

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


def _default_extractor(pdf_path: Path, *, api_key: str) -> dict[str, Any]:
    import os

    os.environ["ANTHROPIC_API_KEY"] = api_key

    from clinical_extractor.extractor import ExtractionError, extract_from_pdf

    try:
        summary = extract_from_pdf(pdf_path)
    except ExtractionError:
        raise
    return summary.model_dump(mode="json")


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

    # ---- 4. Persist temp PDF (extractor espera Path)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="sica-api-", suffix=".pdf", delete=False
        ) as tmp:
            tmp.write(received)
            tmp_path = Path(tmp.name)

        # ---- 5. Ejecutar extractor
        try:
            assert settings.anthropic_api_key is not None  # narrowing for mypy
            payload = extractor(tmp_path, api_key=settings.anthropic_api_key)
        except Exception as exc:  # noqa: BLE001 — surface as 500 sanitized
            error_id = str(uuid.uuid4())
            logger.exception(
                "extract failed",
                extra={
                    "request_id": request_id,
                    "error_id": error_id,
                    "size_bytes": len(received),
                    "exception_type": type(exc).__name__,
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

        # ---- 6. Success
        # NOTE: avoid `filename` as an extra key — it's a reserved
        # LogRecord attribute and the logging module raises KeyError.
        logger.info(
            "extract ok",
            extra={
                "request_id": request_id,
                "uploaded_filename": filename,
                "size_bytes": len(received),
            },
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
