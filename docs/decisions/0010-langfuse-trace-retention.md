# 0010. Política de retención de traces en Langfuse Cloud

- **Status:** Accepted — 2026-05-29 — Implementado
- **Date:** 2026-05-29
- **Deciders:** Aaron Huaynate (founder / CTO)
- **Tags:** observability, langfuse, retention, ley-29733, ops, regulatory
- **Related:** [ADR 0007](0007-langfuse-observability.md) (Langfuse Cloud), [ADR 0009](0009-phi-redaction-in-tracing.md) (PHI redaction — el redactor reduce el riesgo pero no el ciclo de vida), [docs/operations/langfuse-retention.md](../operations/langfuse-retention.md) (procedimiento operacional)

## Context

SICA envía traces a Langfuse Cloud desde 2026-05-26 (ADR-0007). El redactor PHI (ADR-0009) sanitiza identificadores antes del envío. Sin embargo, **falta una política formal de retención**: hoy los traces se acumulan indefinidamente en Langfuse hasta que el plan free hit su cuota.

Drivers que fuerzan tener política antes del primer flujo clínico real (sostenido a partir de mayo–junio 2026):

- **Compliance Ley 29733** (Protección de Datos Personales, Perú). Aunque la PHI directa está redactada (ADR-0009), el `output_json` de cada trace sigue conteniendo metadata clínica (active_problems, lab_results, confidence_score, evidence_spans). La ley exige ciclo de vida definido para todo dato derivado de la paciente, no sólo el identificador directo.
- **Costo y cuota**. Langfuse Cloud free tier limita storage. Crecimiento sin cleanup → degradación de servicio o coste no presupuestado.
- **Auditoría operacional**. Traces antiguos (>6 meses) pierden utilidad marginal pero ocupan espacio que sí necesita el dashboard reciente.
- **Derecho de supresión** (art. 20 Ley 29733). Una titular podría ejercerlo; sin mecanismo de borrado configurable y operable, la respuesta queda atada a vendor support.
- **TODO #3 de ADR-0009** explícitamente dejó abierta la decisión: "definir período máximo de retención y mecanismo de borrado automatizado". Este ADR cierra ese TODO.

## Decision

### Período de retención

**180 días** para todas las traces de SICA en Langfuse Cloud. Aplica uniformemente a production / development / cualquier environment tag.

### Excepciones — traces que NO se borran

Aunque sean más antiguas que 180 días, se preservan:

1. Traces con `scores` no vacíos. Un score en Langfuse es evidencia de evaluación humana (médico colaborador anotó la trace para audit / training / QA). Borrarla destruiría contexto operacional.
2. Traces con tag `preserve`, `audit`, o `reference` (case-insensitive).
3. Traces con `metadata.preserve = true`.

### Mecanismo

- Paquete Python independiente en `scripts/langfuse_retention/`. Instalable con `pip install -e ".[dev]"`. Sin dependencia del extractor ni del API.
- CLI: `sica-langfuse-cleanup [--execute] [--retention-days N] [--output FILE]`.
- API Langfuse usada: `GET /api/public/traces` (listar con `toTimestamp` + paginación) + `DELETE /api/public/traces` (bulk con body `{"traceIds": [...]}`).

### Automatización

- GitHub Actions workflow `.github/workflows/langfuse-cleanup.yml`.
- Cron: cada domingo 03:00 UTC (`0 3 * * 0`).
- Scheduled runs → **siempre dry-run**. Generan un report como artifact (90 días).
- Borrado real → **únicamente `workflow_dispatch` manual** con input `execute=true`.

### Safety

- Piso mínimo de seguridad: **30 días**. El script rechaza `retention_days < 30` con `ValueError`.
- Circuit breaker: **10.000 deletes** por run. Si el query devuelve más, se trunca y se reporta error.
- Batch size: **100 IDs** por bulk delete (1 request por batch en vez de N).
- Rate limit interno: **100 ms** entre batches.
- Default operacional: **dry-run**. El flag `--execute` es la única vía para borrar.

## Rationale

### Por qué 180 días

- Cubre auditoría regulatoria estándar (típicamente 6 meses para historias clínicas en Perú según DIGEMID y MINSA, aunque el dato canónico vive en la HCE local, no en Langfuse).
- Margen sobre los típicos 90 días del free tier sin pagar Pro.
- Balance entre costo y utilidad: traces de hace 6+ meses raramente se consultan para debug operacional.
- Reduce el blast radius de un breach hipotético del provider (menor superficie de PHI residual, aunque el redactor ya minimiza).

### Por qué dry-run default + execute manual

- Borrar traces clínicas es **irreversible**. Un bug en el filtro de fechas o un typo en `--retention-days` puede destruir evidencia.
- Aprobación humana explícita es la única salvaguarda real contra modos de falla del propio script.
- Costo del trade-off: requiere disciplina mensual para hacer el dispatch manual. Aceptable mientras el volumen sea bajo (R1–R2). Si en R3+ el volumen crece, reconsiderar auto-execute con safeguards adicionales.

### Por qué preservar traces con scores

- Score = decisión humana registrada (calidad, anotación, casos para training). Esas traces son evidencia que **no debe perderse por reglas de retención**.
- Crea un mecanismo simple para que el operador marque "no borrar esto": basta con asignar un score desde la UI de Langfuse.
- Equivalente al concepto de "legal hold" para traces específicas.

### Por qué bulk delete sobre individual

- Langfuse expone `DELETE /api/public/traces` con body `{"traceIds": [...]}` (mayo 2026).
- 1 request por batch de 100 IDs vs. 100 requests individuales. Reduce el rate consumido en 100×.
- Simplifica el manejo de errores: una respuesta agregada por batch.
- Trade-off: si el batch falla, perdemos info granular sobre qué IDs específicos del batch fallaron. Aceptable — el próximo run vuelve a intentarlos (idempotencia).

### Por qué `workflow_dispatch` y no auto-execute

- Si un día el script tiene un bug que ignora `dry_run`, los runs auto-ejecutados habrían borrado producción real ya. El gate manual mata esa clase de falla.
- El report semanal por artifact funciona como "pre-mortem": el operador ve qué se borraría antes de confirmar.

## Alternativas consideradas

### Alternativa A: Self-hosted Langfuse con TTL en DB
- **Forma**: Postgres + ClickHouse + S3 propios; TTL declarativo a nivel de DB con políticas de pg_partman o equivalente.
- **Por qué no en R1**: requiere infraestructura nueva (>USD 50/mes, 1-2 días setup + maintenance continuo). Fuera de presupuesto. Misma razón que ADR-0009 § Alternativa A.
- **Cuándo reconsiderar**: R2+ con partner clínico formal, o si emerge requirement de residencia de datos en Perú.

### Alternativa B: Retención más corta (30 / 60 / 90 días)
- **Por qué no**: insuficiente para auditoría regulatoria estándar. Forzaría borrado de traces todavía útiles para debug operacional retrospectivo.
- **30 días** queda como **safety floor** del script, no como política operativa.

### Alternativa C: Retención más larga (365 días o indefinida)
- **Por qué no**: excede mejor práctica de minimización de datos. Aumenta superficie de riesgo PHI residual. Sin beneficio operacional incremental (un trace de 11 meses casi nunca se consulta).

### Alternativa D: Cleanup manual sin automatización
- **Por qué no**: requiere disciplina humana sin scaffolding. No escalable. Lleva a olvidos.
- El workflow scheduled (dry-run semanal) provee el scaffolding sin forzar borrado.

### Alternativa E: Auto-execute en el cron (sin gate manual)
- **Por qué no**: bug en el filtro de fechas → borrado real automático → traces perdidas sin posibilidad de revisión. El costo del gate manual (1 click mensual) es muy bajo comparado al riesgo.
- Reconsiderar si el volumen crece y el gate manual se vuelve cuello de botella.

## Consequences

### Positivas

- **Compliance Ley 29733** con ciclo de vida explícito y mecanismo de derecho de supresión.
- **Costo predecible**: el storage en Langfuse Cloud no crece indefinidamente.
- **Auditoría regulatoria** con período definido y documentado.
- **Reversible**: cambiar `LANGFUSE_RETENTION_DAYS` o el cron en el workflow sin redeploy del extractor.
- **Safety triple**: piso 30 días en código + dry-run default + workflow gate manual.

### Negativas

- **Borrado asíncrono**: Langfuse procesa el delete en backend (hasta ~15 min). El report del script reporta "deleted" cuando el endpoint **aceptó** el batch, no cuando lo materializó. Verificación de borrado físico requiere segundo run.
- **Recuperación post-error**: si el script borra accidentalmente (bug + execute manual del operador), la recuperación depende del soft-delete policy de Langfuse (no completamente documentado al momento de este ADR; assumed irreversible).
- **Scheduled dry-run NO previene acumulación por sí mismo** — requiere disciplina humana de revisar reportes y disparar execute mensual. Si nadie lo hace, los traces se acumulan igual.
- **Falsos negativos en preservación**: un trace que el operador olvidó scorear se borra a los 180 días aun si era importante. Mitigación: documentación operacional + opción de "execute" requiere revisión humana.

### Neutras

- No afecta arquitectura técnica del extractor ni de apps/api.
- Independiente del frontend.
- Si en futuro se migra a Langfuse self-hosted, el script puede apuntar a esa URL con cambio de `LANGFUSE_BASE_URL` (la API es la misma).

## Plan operacional

### Semanal (automático)
- Cron domingo 03:00 UTC → `dry-run` → report como artifact GitHub Actions (90 días retención).

### Mensual recomendado (manual)
1. Lunes después del cuarto scheduled run del mes:
   - Actions → Langfuse Retention Cleanup → último run → descargar `cleanup-report-{run_id}` artifact.
   - Revisar el JSON: `inspected`, `eligible_for_delete`, `preserved`, `errors`.
2. Si el report es razonable (`eligible_for_delete < 10000`, `errors == []`):
   - Actions → Langfuse Retention Cleanup → Run workflow → execute: `true`.
3. Verificar en el próximo dry-run que `eligible_for_delete` bajó.

### Trimestral (revisión política)
- Validar que 180 días sigue siendo adecuado.
- Ajustar si emergen requirements regulatorios nuevos (ANPD guidance, partner clínico, etc.).
- Actualizar este ADR si cambia política.

## Referencias

- [ADR 0007](0007-langfuse-observability.md) — Langfuse Cloud (provider).
- [ADR 0009](0009-phi-redaction-in-tracing.md) — Redactor PHI (background regulatorio + § TODOs R2+ que abrió la necesidad de retención).
- [scripts/langfuse_retention/](../../scripts/langfuse_retention/) — implementación del script (cleanup.py, cli.py, tests).
- [.github/workflows/langfuse-cleanup.yml](../../.github/workflows/langfuse-cleanup.yml) — automatización.
- [docs/operations/langfuse-retention.md](../operations/langfuse-retention.md) — procedimiento operacional para el operador.
- **Ley 29733** — Ley de Protección de Datos Personales del Perú. Reglamento DS 003-2013-JUS. Artículos relevantes: 11 (calidad), 20 (derecho de supresión).
- **Langfuse API docs** (mayo 2026): `GET /api/public/traces`, `DELETE /api/public/traces`.

## Revisión

Este ADR se revisa explícitamente en uno de estos triggers:

- **Volumen mensual de traces supera 10K** → revisar circuit breaker + page sizes.
- **Aparece presupuesto/partner para self-hosted** → posiblemente desactivar el cleanup automático (la DB self-hosted aplicaría TTL nativo).
- **ANPD emite guidance sobre retención de logs LLM en healthtech** → adaptar período.
- **El operador reporta que el flujo mensual es cuello de botella** → considerar auto-execute con safeguards adicionales (alerting, dry-run pre-check, etc.).

Hasta entonces, **180 días + workflow gate manual** es la configuración operativa.

## Migration log

| Fecha | Cambio | Autor | ADR superseder |
|---|---|---|---|
| 2026-05-29 | Creación inicial — política + script + workflow | Aaron Huaynate | — |
