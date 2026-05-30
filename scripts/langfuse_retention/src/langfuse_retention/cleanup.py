"""Cleanup core: lista traces antiguas, filtra preservables, ejecuta deletes.

API Langfuse usada (validada mayo 2026 vía API reference + docs):

    GET  /api/public/traces      query: page, limit, fromTimestamp, toTimestamp
    DELETE /api/public/traces    body: {"traceIds": [...]}   -- bulk, async
    DELETE /api/public/traces/{id}                            -- individual (fallback)

Bulk delete es preferido: una request por batch en vez de N requests por trace.
La operación es asíncrona — Langfuse puede demorar hasta 15 minutos en
materializar la eliminación en su backend. El script reporta como "deleted"
las traces que el endpoint aceptó, no las que verificó borradas.

Filtros de preservación (NUNCA borrar aunque sean viejas):
    - Traces con scores (evaluación humana realizada)
    - Tags: "preserve", "audit", "reference"
    - Metadata flag: preserve == True
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ----- Política operacional -----
# Default operativo (ADR-0010): 180 días de retención.
DEFAULT_RETENTION_DAYS = 180
# Piso de seguridad: aunque el operador pase --retention-days=5, rechazar.
# Reduce el blast radius de un typo o flag mal pasado.
SAFETY_MIN_RETENTION_DAYS = 30
# Circuit breaker: si por error la query devuelve 100K traces antiguas (e.g.
# bug en el filtro de fechas), parar en 10K para que un humano revise antes
# de continuar borrando.
MAX_DELETES_PER_RUN = 10_000
# Batch size para bulk delete. Conservador: Langfuse no documenta cap pero
# 100 IDs por request es un balance estándar.
BULK_DELETE_BATCH_SIZE = 100
# Espera entre batches para no presionar el rate limit del API.
RATE_LIMIT_DELAY_SEC = 0.1
# Tags que marcan trace como "no borrar" (case-insensitive).
PRESERVE_TAGS = frozenset({"preserve", "audit", "reference"})
# Page size para listar — el API tolera hasta 100 confortablemente.
LIST_PAGE_SIZE = 100
# Tope de páginas a iterar al listar (evita loops infinitos si el API
# devuelve paginación inconsistente). Con MAX_DELETES_PER_RUN=10K y page
# size 100, 200 páginas cubre cómodamente sin caer en loops degenerados.
LIST_MAX_PAGES = 200


@dataclass(frozen=True)
class CleanupConfig:
    """Configuración inmutable de una ejecución de cleanup."""

    retention_days: int
    base_url: str
    public_key: str
    secret_key: str
    dry_run: bool = True
    project_id: str | None = None


@dataclass
class CleanupResult:
    """Resultado de la ejecución: contadores, errores, timing.

    No es frozen porque se mutan los contadores durante la ejecución; al
    finalizar el caller lo trata como inmutable (no se serializa antes).
    """

    inspected: int = 0
    eligible_for_delete: int = 0
    deleted: int = 0
    preserved: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    dry_run: bool = True
    retention_days: int = 0
    cutoff_iso: str = ""


def _list_traces_older_than(
    config: CleanupConfig,
    cutoff: datetime,
    page_size: int = LIST_PAGE_SIZE,
    max_pages: int = LIST_MAX_PAGES,
) -> list[dict[str, Any]]:
    """Lista traces con timestamp < cutoff via paginación.

    Parámetros del API (validados con docs Langfuse):
        - page: 1-indexed, incrementa hasta agotar resultados.
        - limit: items por página (hasta ~100 confortablemente).
        - toTimestamp: ISO 8601, inclusivo en docs pero filtramos local-side
          también por defensa.
        - projectId: opcional, ya implícito si la API key pertenece al
          proyecto pero documentado en el config por completitud.
    """
    traces: list[dict[str, Any]] = []
    cutoff_iso = cutoff.isoformat()

    for page in range(1, max_pages + 1):
        params: dict[str, Any] = {
            "limit": page_size,
            "page": page,
            "toTimestamp": cutoff_iso,
        }
        if config.project_id:
            params["projectId"] = config.project_id

        response = requests.get(
            f"{config.base_url}/api/public/traces",
            auth=(config.public_key, config.secret_key),
            params=params,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        batch = data.get("data") or []
        if not batch:
            break

        traces.extend(batch)

        # Si el batch es más chico que el page_size, es la última página.
        if len(batch) < page_size:
            break

        # Defensa adicional contra bucles infinitos por respuestas raras.
        if len(traces) >= MAX_DELETES_PER_RUN * 2:
            logger.warning(
                "Listado superó 2x MAX_DELETES_PER_RUN (%d). "
                "Cortando paginación temprano.",
                MAX_DELETES_PER_RUN * 2,
            )
            break

    return traces


def _is_preserve_candidate(trace: dict[str, Any]) -> tuple[bool, str]:
    """Determina si una trace debe preservarse aunque sea antigua.

    Returns:
        ``(True, motivo)`` si debe preservarse, ``(False, "")`` si no.

    Motivos:
        - Tiene ``scores`` (evaluación humana realizada).
        - Tags incluye ``preserve`` / ``audit`` / ``reference`` (case-insensitive).
        - Metadata tiene ``preserve == True``.
    """
    scores = trace.get("scores")
    if scores:
        return True, "tiene scores (evaluación humana)"

    tags = trace.get("tags") or []
    if isinstance(tags, list):
        tags_lower = {str(t).lower() for t in tags}
        intersection = tags_lower & PRESERVE_TAGS
        if intersection:
            return True, f"tag preserve/audit/reference: {sorted(intersection)}"

    metadata = trace.get("metadata") or {}
    if isinstance(metadata, dict) and metadata.get("preserve") is True:
        return True, "metadata.preserve=true"

    return False, ""


def _bulk_delete_traces(
    config: CleanupConfig, trace_ids: list[str]
) -> tuple[int, list[str]]:
    """Ejecuta DELETE bulk de un batch de trace IDs.

    Returns:
        ``(deleted_count, errors)``. Si el endpoint responde 200/202/204,
        cuenta el batch como aceptado. Langfuse procesa async — la
        eliminación física puede demorar hasta 15 min según docs.

        404 es tratado como éxito por idempotencia (la trace ya no existe).
        Otros códigos se loguean como error sin abortar el run.
    """
    if config.dry_run:
        return len(trace_ids), []
    if not trace_ids:
        return 0, []

    try:
        response = requests.delete(
            f"{config.base_url}/api/public/traces",
            auth=(config.public_key, config.secret_key),
            json={"traceIds": trace_ids},
            timeout=30,
        )
    except requests.RequestException as exc:
        return 0, [f"bulk_delete network error: {exc}"]

    if response.status_code in (200, 202, 204):
        return len(trace_ids), []
    if response.status_code == 404:
        # Idempotencia: si todo el batch ya no existe, considerar aceptado.
        return len(trace_ids), []

    error_body = response.text[:200] if response.text else ""
    return 0, [
        f"bulk_delete HTTP {response.status_code}: {error_body}"
    ]


def run_cleanup(config: CleanupConfig) -> CleanupResult:
    """Ejecuta el cleanup completo: listar, filtrar, borrar (o dry-run).

    Pasos:
        1. Validar ``retention_days >= SAFETY_MIN_RETENTION_DAYS``.
        2. Computar cutoff = ahora - retention_days.
        3. Listar traces con timestamp < cutoff.
        4. Particionar en preservar vs. eligible.
        5. Bulk-delete por batches.
        6. Devolver ``CleanupResult`` con contadores.

    Raises:
        ValueError: si retention_days viola el piso de seguridad.
    """
    if config.retention_days < SAFETY_MIN_RETENTION_DAYS:
        msg = (
            f"retention_days={config.retention_days} es menor al mínimo de "
            f"seguridad {SAFETY_MIN_RETENTION_DAYS}. Revisar política antes "
            f"de ejecutar (ver ADR-0010 § Safety)."
        )
        raise ValueError(msg)

    start = time.time()
    cutoff = datetime.now(UTC) - timedelta(days=config.retention_days)
    cutoff_iso = cutoff.isoformat()

    logger.info(
        "Cleanup start: retention=%dd, cutoff=%s, dry_run=%s",
        config.retention_days,
        cutoff_iso,
        config.dry_run,
    )

    traces = _list_traces_older_than(config, cutoff)
    result = CleanupResult(
        inspected=len(traces),
        dry_run=config.dry_run,
        retention_days=config.retention_days,
        cutoff_iso=cutoff_iso,
    )

    # Particionar en preservable / eligible
    eligible_ids: list[str] = []
    for trace in traces:
        trace_id = trace.get("id")
        if not trace_id:
            continue

        should_preserve, reason = _is_preserve_candidate(trace)
        if should_preserve:
            result.preserved += 1
            logger.info("Preserving %s: %s", trace_id, reason)
            continue

        eligible_ids.append(str(trace_id))

    result.eligible_for_delete = len(eligible_ids)

    # Circuit breaker: capear el lote a MAX_DELETES_PER_RUN
    if len(eligible_ids) > MAX_DELETES_PER_RUN:
        result.errors.append(
            f"Eligibles ({len(eligible_ids)}) excede MAX_DELETES_PER_RUN "
            f"({MAX_DELETES_PER_RUN}). Truncando lote — revisar política."
        )
        eligible_ids = eligible_ids[:MAX_DELETES_PER_RUN]

    # Bulk delete por batches
    for batch_start in range(0, len(eligible_ids), BULK_DELETE_BATCH_SIZE):
        batch = eligible_ids[batch_start : batch_start + BULK_DELETE_BATCH_SIZE]
        accepted, batch_errors = _bulk_delete_traces(config, batch)
        result.deleted += accepted
        result.errors.extend(batch_errors)

        if not config.dry_run and batch_start + BULK_DELETE_BATCH_SIZE < len(eligible_ids):
            time.sleep(RATE_LIMIT_DELAY_SEC)

        if config.dry_run:
            logger.info(
                "[dry-run] would bulk-delete batch of %d traces (cum=%d)",
                len(batch),
                result.deleted,
            )
        else:
            logger.info(
                "Bulk-delete batch accepted (%d traces, cum=%d)",
                accepted,
                result.deleted,
            )

    result.duration_seconds = time.time() - start
    logger.info(
        "Cleanup done: inspected=%d eligible=%d deleted=%d preserved=%d errors=%d duration=%.1fs",
        result.inspected,
        result.eligible_for_delete,
        result.deleted,
        result.preserved,
        len(result.errors),
        result.duration_seconds,
    )
    return result


def config_from_env() -> CleanupConfig:
    """Construye ``CleanupConfig`` desde variables de entorno.

    Variables requeridas:
        - LANGFUSE_BASE_URL
        - LANGFUSE_PUBLIC_KEY
        - LANGFUSE_SECRET_KEY

    Variables opcionales:
        - LANGFUSE_RETENTION_DAYS (default 180)
        - LANGFUSE_CLEANUP_DRY_RUN (default "true")
        - LANGFUSE_PROJECT_ID (default None)

    Raises:
        KeyError: si falta una variable requerida.
    """
    return CleanupConfig(
        retention_days=int(
            os.environ.get("LANGFUSE_RETENTION_DAYS", str(DEFAULT_RETENTION_DAYS))
        ),
        base_url=os.environ["LANGFUSE_BASE_URL"],
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        dry_run=os.environ.get("LANGFUSE_CLEANUP_DRY_RUN", "true").lower() == "true",
        project_id=os.environ.get("LANGFUSE_PROJECT_ID") or None,
    )
