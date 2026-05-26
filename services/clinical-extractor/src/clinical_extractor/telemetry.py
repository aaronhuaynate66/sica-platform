"""Telemetría estructurada del clinical-extractor.

Cada extracción emite **un único registro JSON-line** a stdout/stderr
con los campos relevantes para auditoría y debugging — NUNCA con
contenido del PDF ni con PHI:

    {
      "timestamp": "2026-05-22T05:30:00Z",
      "operation_id": "...uuid...",
      "pdf_size_bytes": 5626,
      "pages_extracted": 2,
      "model_used": "claude-sonnet-4-5-20250929",
      "prompt_version": "0.1.0",
      "latency_ms": 1840,
      "retry_count": 0,
      "success": true,
      "error_type": null,
      "token_usage": {"input_tokens": 1234, "output_tokens": 567}
    }

Para activar la emisión a stdout configurar el logger
`clinical_extractor.telemetry` con un StreamHandler. La CLI lo hace
automáticamente. Cuando el extractor se usa como librería, el caller
decide dónde van los logs (default: silencioso).

Coherente con ADR 0004 Nivel 4 — los campos aquí son un subset
operacional del audit trail completo definido en ese ADR.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import IO, Any

TELEMETRY_LOGGER_NAME = "clinical_extractor.telemetry"


class _JsonLineFormatter(logging.Formatter):
    """Empaqueta el record entero como una línea JSON UTF-8."""

    def format(self, record: logging.LogRecord) -> str:
        # El mensaje ya es un JSON serializable (dict pasado vía `extra={"payload": ...}`).
        payload = getattr(record, "payload", None)
        if payload is None:
            payload = {"msg": record.getMessage()}
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def configure_stream_handler(stream: IO[str] = sys.stderr, level: int = logging.INFO) -> None:
    """Conecta el telemetry logger a un stream con formato JSON-line.

    Idempotente: re-llamar no duplica handlers.
    """
    logger = logging.getLogger(TELEMETRY_LOGGER_NAME)
    logger.setLevel(level)
    # Evitar handlers duplicados si la función se llama varias veces.
    for h in logger.handlers:
        if getattr(h, "_sica_telemetry", False):
            return
    handler = logging.StreamHandler(stream)
    handler.setFormatter(_JsonLineFormatter())
    handler._sica_telemetry = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    logger.propagate = False


def emit(payload: dict[str, Any]) -> None:
    """Emite un evento de telemetría.

    El caller pasa un dict ya estructurado. Esta función NO añade campos
    automáticos (timestamp, operation_id) — el caller los compone para
    mantener el contrato explícito y testeable.
    """
    logging.getLogger(TELEMETRY_LOGGER_NAME).info("telemetry", extra={"payload": payload})
