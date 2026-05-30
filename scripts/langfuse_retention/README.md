# SICA Langfuse Retention

Auto-cleanup de traces antiguas en Langfuse Cloud según política definida en
[ADR-0010](../../docs/decisions/0010-langfuse-trace-retention.md).

## Política

- Retención default: **180 días**.
- Mínimo de seguridad: **30 días** (el script rechaza valores menores).
- Filtros de preservación (NUNCA se borran):
  - Traces con `scores` (evaluación humana realizada).
  - Tags: `preserve`, `audit`, `reference`.
  - Metadata `preserve == true`.
- Borrado **asíncrono**: Langfuse procesa el delete en backend y puede
  demorar hasta ~15 minutos en materializarse.

## API Langfuse usada

| Método | Path | Uso |
| --- | --- | --- |
| `GET` | `/api/public/traces` | listar con `fromTimestamp` / `toTimestamp`, paginación |
| `DELETE` | `/api/public/traces` | bulk delete con body `{"traceIds": [...]}` |

Bulk delete: 1 request por batch de hasta 100 IDs en vez de 1 por trace.
Reduce el rate consumido en órdenes de magnitud y simplifica el manejo de
errores.

## Uso local

```bash
cd scripts/langfuse_retention
python -m pip install -e ".[dev]"

# Dry-run (NO borra nada, sólo reporta qué borraría)
export LANGFUSE_BASE_URL=https://us.cloud.langfuse.com
export LANGFUSE_PUBLIC_KEY=...
export LANGFUSE_SECRET_KEY=...
sica-langfuse-cleanup --verbose

# Ejecutar deletes reales (¡irreversible! ver § "Cuándo NO hacer execute"
# en docs/operations/langfuse-retention.md)
sica-langfuse-cleanup --execute --verbose

# Override de retención para una ejecución puntual
sica-langfuse-cleanup --retention-days 120 --verbose

# Reporte JSON a archivo
sica-langfuse-cleanup --output cleanup-report.json
```

## Uso en CI

Workflow: [`.github/workflows/langfuse-cleanup.yml`](../../.github/workflows/langfuse-cleanup.yml).

- Scheduled: cada domingo 03:00 UTC → siempre **dry-run**.
- Borrado real: `workflow_dispatch` manual con input `execute=true`.

## Variables de entorno

| Variable | Default | Descripción |
| --- | --- | --- |
| `LANGFUSE_BASE_URL` | (requerido) | URL del Langfuse Cloud (e.g. `https://us.cloud.langfuse.com`) |
| `LANGFUSE_PUBLIC_KEY` | (requerido) | Public key del proyecto |
| `LANGFUSE_SECRET_KEY` | (requerido) | Secret key del proyecto |
| `LANGFUSE_RETENTION_DAYS` | `180` | Días de retención |
| `LANGFUSE_CLEANUP_DRY_RUN` | `true` | Si `true`, no borra. CLI flag `--execute` lo override. |
| `LANGFUSE_PROJECT_ID` | `None` | Filtrar a un proyecto específico (opcional) |

## Salvaguardas

- Piso de seguridad **30 días**: `--retention-days 5` levanta `ValueError`.
- Circuit breaker **10.000 deletes**: si el query devuelve más, se trunca y
  se reporta el error sin borrar más allá.
- Batch size **100**: lotes pequeños evitan timeouts y permiten retry parcial.
- Rate limit **10 req/s** entre batches (`time.sleep(0.1)`).

## Tests

```bash
cd scripts/langfuse_retention
python -m pytest -v
```
