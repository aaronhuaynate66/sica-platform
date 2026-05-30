# Operación: Retención de Traces Langfuse

> **Documento operacional, no normativo.** La política está en [ADR-0010](../decisions/0010-langfuse-trace-retention.md). Este documento traduce esa política a procedimientos concretos.
>
> Audiencia: founder / ops responsable de ejecutar el cleanup mensual y responder solicitudes de derecho de supresión.

---

## TL;DR

- **Retención**: 180 días.
- **Scheduled dry-run**: cada domingo 03:00 UTC → siempre dry-run → report como artifact.
- **Borrado real**: `workflow_dispatch` manual con `execute=true`. Único camino.
- **Reports**: artifacts del workflow, retenidos 90 días.

---

## Setup inicial — secrets de GitHub Actions

Antes del primer run scheduled, el repo necesita 3 secrets configurados.

### Cómo configurarlos

1. GitHub → `aaronhuaynate66/sica-platform` → **Settings**.
2. **Secrets and variables** → **Actions** → **New repository secret**.
3. Agregar uno por uno:

| Name | Value | De dónde sale |
| --- | --- | --- |
| `LANGFUSE_BASE_URL` | `https://us.cloud.langfuse.com` | Default actual (US region) |
| `LANGFUSE_PUBLIC_KEY` | `pk-lf-...` | Langfuse dashboard → Settings → API keys |
| `LANGFUSE_SECRET_KEY` | `sk-lf-...` | Idem, **mismo proyecto** que el del extractor |

> **Importante**: el par `public_key` + `secret_key` debe ser del **mismo proyecto** Langfuse donde el extractor está enviando los traces. Si el extractor en Render usa un proyecto y el cleanup apunta a otro, no borra nada.

### Verificación

Tras configurar los secrets, lanzar un **dry-run manual** desde la UI:

1. Actions → **Langfuse Retention Cleanup** → **Run workflow**.
2. Branch: `main`. Execute: `false`. Retention_days: vacío.
3. Esperar el run (~1-2 min).
4. Abrir el run → step **Run cleanup** → confirmar que loguea `inspected=N` con N coherente.
5. Descargar artifact `cleanup-report-{run_id}` y revisar el JSON.

Si `inspected=0` y no hubo errores HTTP en el log, los secrets están OK pero no hay traces antiguas (esperado en R1 reciente).

---

## Cronograma operativo

### Semanal (automático)
- Domingo 03:00 UTC: run scheduled → dry-run → report subido como artifact.
- **No requiere acción humana**, sólo está disponible para revisar si se quiere.

### Mensual recomendado
1. **Lunes de la última semana del mes** (o el día que se prefiera):
   - Actions → Langfuse Retention Cleanup → último run.
   - Descargar artifact `cleanup-report-{run_id}`.
   - Abrir el JSON; revisar:
     - `inspected`: cuántas traces totales hay con timestamp > 180 días.
     - `eligible_for_delete`: cuántas pasarían el filtro de preservación.
     - `preserved`: cuántas tienen score / tag / metadata-flag y NO se borrarían.
     - `errors`: debe ser `[]`.

2. **Si el report es razonable** (`eligible_for_delete` < 10.000 y `errors=[]`):
   - Actions → Langfuse Retention Cleanup → **Run workflow**.
   - Branch: `main`.
   - Execute: **`true`**.
   - Retention_days: vacío (usa 180 default).
   - **Run**.

3. **Verificar** en el próximo dry-run (siguiente domingo) que `eligible_for_delete` bajó significativamente.

### Trimestral (revisión política)

- Revisar [ADR-0010 § Revisión](../decisions/0010-langfuse-trace-retention.md). Validar que 180 días sigue siendo adecuado.
- Si emerge necesidad de cambio, actualizar el ADR + abrir issue de seguimiento.

---

## Ejecutar desde local (debug / pre-prod)

```bash
cd scripts/langfuse_retention
python -m pip install -e ".[dev]"

# Dry-run con env vars manuales
export LANGFUSE_BASE_URL=https://us.cloud.langfuse.com
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
sica-langfuse-cleanup --verbose

# Override de retention para una ejecución puntual
sica-langfuse-cleanup --retention-days 200 --verbose

# Execute REAL (¡cuidado, irreversible!)
sica-langfuse-cleanup --execute --verbose
```

---

## Cuándo NO hacer execute

Hay condiciones en las que el operador debe **pausar el cleanup** aunque el report sea automático:

- **`eligible_for_delete` > 10.000**: anormal. Investigar antes (¿el extractor produjo más volumen de lo esperado? ¿filtro de fecha desalineado?).
- **`errors` no vacío**: revisar primero si Langfuse Cloud tiene incidencia.
- **Auditoría inminente** (regulatoria, partner clínico): pausar hasta cerrar la auditoría.
- **Problema reciente con el extractor**: traces de la semana podrían ser útiles para debug. No correr execute con `--retention-days < 180`.

---

## Derecho de supresión — flujo manual

Si una titular ejerce derecho de supresión (Ley 29733 art. 20) sobre datos específicos:

1. Confirmar que la titular efectivamente fue procesada por SICA (registros del médico colaborador + logs locales de `apps/api`).
2. Cruzar fecha de procesamiento + `request_id` con traces en Langfuse Cloud.
3. **En el dashboard de Langfuse**, eliminar manualmente los traces relevantes (UI → trace → menú → Delete).
4. Documentar la acción en hoja externa de tracking (fecha, motivo, IDs de trace eliminados, sin nombre de la titular).

El cleanup automático **NO sustituye** este flujo — el cleanup es por edad temporal; el derecho de supresión es por solicitud explícita.

---

## Cómo preservar traces específicas (sobrescribir el cleanup)

Opciones para evitar que una trace antigua se borre cuando llegue a los 180 días:

1. **Agregar score** desde el dashboard Langfuse:
   - Tracing → trace → **Add score** → cualquier valor (e.g. `manual_review = 1`).
   - Mecánica: el script preserva traces con `scores` no vacíos.

2. **Agregar tag**:
   - Tracing → trace → **Tags** → uno de `preserve`, `audit`, `reference` (case-insensitive).

3. **Editar metadata** (programáticamente):
   - PATCH al trace con `metadata.preserve = true`.

---

## Anatomía del reporte JSON

Ejemplo (dry-run, después de algunos meses de uso):

```json
{
  "inspected": 1247,
  "eligible_for_delete": 1198,
  "deleted": 1198,
  "preserved": 49,
  "errors": [],
  "duration_seconds": 18.4,
  "dry_run": true,
  "retention_days": 180,
  "cutoff_iso": "2025-11-30T03:00:00+00:00"
}
```

| Campo | Interpretación |
| --- | --- |
| `inspected` | Traces con timestamp anterior al cutoff |
| `eligible_for_delete` | Subset de inspected que pasa el filtro de preservación |
| `deleted` | En `dry_run=true`: hipotético. En execute real: aceptado por el endpoint (no necesariamente materializado todavía) |
| `preserved` | Inspected que tenían score / tag / metadata-flag y NO se borraron |
| `errors` | Lista de strings; vacío = run limpio |
| `duration_seconds` | Tiempo total wall-clock |
| `dry_run` | El flag efectivo del run |
| `retention_days` | Política usada |
| `cutoff_iso` | Fecha límite calculada (ISO 8601, UTC) |

---

## Limitaciones conocidas

1. **Borrado asíncrono**. El bulk delete de Langfuse acepta la request inmediatamente pero procesa en backend. Materialización puede demorar hasta ~15 minutos. El campo `deleted` del reporte refleja "aceptado por el endpoint", no "borrado físicamente confirmado". Para verificar borrado físico: correr otro dry-run después de 30 min y confirmar que `inspected` bajó.

2. **Soft-delete no documentado**. La política de Langfuse sobre recuperación post-delete no está totalmente clara al momento de este documento (mayo 2026). Asumir que el borrado es **definitivo**.

3. **Scheduled run no previene acumulación por sí mismo**. Es un dry-run informativo. Requiere disciplina humana de ejecutar `workflow_dispatch` con `execute=true` periódicamente. Si nadie lo hace por meses, los traces se acumulan igual.

4. **Sin alerting automático sobre anomalías**. Si el report semanal muestra `eligible_for_delete=50.000` por un bug del extractor, nadie es notificado proactivamente. Mitigación R2+: integrar alerting (Slack/email) cuando el report exceda un threshold.

5. **No hay validación de proyecto Langfuse**. El script confía en que las credenciales apuntan al proyecto correcto. Si por error se configuran credenciales de otro proyecto, el cleanup actúa sobre traces equivocadas.

---

## TODOs futuros (R2+)

- **Auto-tagging de traces críticas** (e.g. `confidence_score < 0.7` → auto-tag `review`) para asegurar preservación automática de casos relevantes.
- **Métricas y dashboard**: graficar cuántas traces se borraron por mes vs cuántas se preservaron.
- **Alerting** sobre reports anómalos (eligible muy alto, errors no vacío).
- **Validación de proyecto**: el script podría chequear `GET /api/public/projects` y rechazar si el `project_id` resuelto no matchea uno esperado.
- **Integración con derechos de supresión**: API o flow que el partner clínico pueda disparar directamente.

---

## Referencias

- [ADR-0010](../decisions/0010-langfuse-trace-retention.md) — Política normativa.
- [ADR-0007](../decisions/0007-langfuse-observability.md) — Langfuse Cloud (provider).
- [ADR-0009](../decisions/0009-phi-redaction-in-tracing.md) — Redactor PHI.
- [scripts/langfuse_retention/README.md](../../scripts/langfuse_retention/README.md) — Documentación del paquete y API Langfuse usada.

---

## Cambios

| Fecha | Cambio | Autor |
|---|---|---|
| 2026-05-29 | Creación inicial. Captura procedimiento operacional del primer release del cleanup. | Aaron Huaynate |
