# 0007. Langfuse Cloud para observability LLM

- **Status:** Accepted — 2026-05-26 — Implementado
- **Date:** 2026-05-26
- **Deciders:** Aaron Huaynate (founder / CTO)
- **Tags:** observability, llm, tracing, costos, infra
- **Related:** [ADR 0003](0003-security-and-phi-policy.md) (PHI policy), [ADR 0004](0004-model-routing-policy.md) (model routing), [ADR 0006](0006-render-config-precedence.md) (Render config), [issue #14](https://github.com/aaronhuaynate66/sica-platform/issues/14) (Setup Langfuse self-hosted o decisión de servicio gestionado)

## Context

A medida que `clinical-extractor` se acerca a uso real (R1 con datos sintéticos + R2 shadow mode), necesitamos visibilidad operacional de cada llamada a un LLM:

- **Costos por extracción.** El extractor cobra USD por token (Anthropic). Sin telemetría agregada, no sabemos si una sesión costó USD 0.10 o USD 10.00 hasta ver la factura mensual. Para presupuestar correctamente R1 y negociar precio con un partner, necesitamos costo por extracción y costo por mes desglosados por modelo / caso / volumen.
- **Latencia P50/P95 en producción.** Un extractor que tarda 20s end-to-end es aceptable para batch nocturno; uno que tarda 60s no es usable en flujo clínico interactivo. El número exacto sólo se conoce midiendo runs reales contra PDFs reales.
- **Debugging de outputs problemáticos.** Cuando una extracción produce una omisión crítica o una hallucination en R2 shadow mode, necesitamos poder navegar al request original — qué prompt corrió, qué tokens entraron, qué output devolvió el modelo — sin tener que reproducir manualmente. El harness de evaluación (ver ADR 0005) hace esto para datasets curados, pero no para casos espontáneos en producción.
- **Comparación entre providers.** Cuando MedGemma 4B esté disponible (issue #12), querremos comparar Claude Sonnet vs MedGemma 4B contra los mismos PDFs en términos de costo, latencia y factual_accuracy. Necesitamos infra para registrar ambas corridas en formato comparable.

La pregunta del issue #14 era: **Langfuse self-hosted o servicio gestionado**. Esta decisión documenta la elección y las trade-offs.

## Decision

**SICA usa Langfuse Cloud (US region) como provider de observability LLM en R0/R1.** Se integra al `clinical-extractor` vía el SDK Python `langfuse>=3.0.0,<4.0.0`, con tracing automático en `AnthropicProvider.extract()`.

Detalles técnicos:

- **Region:** US (`https://us.cloud.langfuse.com`). Diferencia con EU: latencia +50ms desde Perú vs ~100ms desde Europa; pricing idéntico. Elegido US para no agregar consideraciones de GDPR mientras no procesemos PHI europea.
- **SDK version:** v3.x con **pin estricto `<4.0.0`**. La v4 (lanzada 2026-04) introdujo cambios breaking: renombró env vars (`LANGFUSE_BASEURL` → `LANGFUSE_BASE_URL`), cambió la API de `CallbackHandler`, y aún tiene tickets abiertos de migración. Quedarse en v3 hasta que v4 madure (probablemente Q3 2026).
- **Pricing table estática** (`pricing.py`) en lugar de query a Anthropic billing API:
  - Anthropic publica precios oficiales en https://www.anthropic.com/pricing y los cambia ocasionalmente. Tener la tabla en código fuente hace que cualquier cambio quede en commit log con review explícito.
  - Evita una dependencia adicional al SDK de billing.
  - Si el modelo no está en la tabla, `calculate_cost_usd` devuelve `None` — el caller registra el trace sin `cost_details`, en vez de fallar.
- **Sampling.** `LANGFUSE_SAMPLE_RATE=1.0` por default (trazar todas las extracciones). Configurable via env var. Reevaluar en R2 si el volumen crece y los costos del Cloud plan justifican muestreo.
- **Environment tag** (`LANGFUSE_TRACING_ENVIRONMENT`) — separa prod/staging/dev en el dashboard. Default `"production"`.
- **Fallback graceful obligatorio.** Si Langfuse Cloud cae, si las credenciales son inválidas, si el SDK levanta una excepción interna — **el extractor sigue funcionando**. La función `trace_extraction` envuelve toda la lógica de Langfuse en `try/except`, loggea como warning, y retorna. Adicionalmente, `_safe_trace` en `anthropic_provider.py` envuelve incluso el `import` por si el módulo de tracing se rompiera al cargar. Doble cinturón.
- **Sin propagación de trace context al frontend / API por ahora.** El `apps/api` no envía un trace ID al extractor; cada extracción es su propio trace top-level. Cuando R1 introduzca un orquestador con múltiples LLM calls (resumen + care gaps + handoff), evaluamos jerarquía con `start_as_current_span` y propagación entre servicios.

## Consequences

### Positive

- **Visibilidad inmediata de cada extracción** en https://us.cloud.langfuse.com. Cada trace muestra: case_id, modelo, tokens, latencia, output JSON completo, costo USD.
- **Costo USD por trace** calculado automáticamente desde la tabla de pricing local. Sin esto, costo agregado mensual requiere parsear billing logs de Anthropic.
- **Latencia tracked** end-to-end con resolución de ms. Permite alertar sobre regresión de performance (p. ej. cambio de prompt que duplica el tiempo).
- **Listo para comparar providers** cuando MedGemma esté disponible. Ambos providers van a llamar `trace_extraction` con el mismo schema, así que el dashboard de Langfuse puede agruparlos en una sola vista (filtrar por `metadata.provider_id`).
- **Errors flagged como `level=ERROR`** — el dashboard muestra fallos prominentemente. Antes solo aparecían en logs locales / stderr.
- **Auditoría más simple** para regulación. STRATEGY § 13 pide trazabilidad de cada decisión asistida; Langfuse trazas son una capa concreta de evidencia (con limitaciones — ver § Privacidad).

### Negative

- **Dependency externa adicional** (`langfuse` SDK, ~5 MB instalado, ~12 dependencias transitivas). Sumamos cara visible de ataque + más código que mantener actualizado.
- **Overhead ~50-100ms por extracción.** El SDK flushea async cada N segundos, así que la latencia del request principal no se ve afectada significativamente — la latencia visible sólo es el costo de `start_observation` (sincrónico) + `flush` al final. Medido en smoke test: 19.5s totales vs ~19.4s sin tracing.
- **Pricing futuro de Langfuse Cloud puede cambiar.** Hoy plan free de Langfuse cubre los volúmenes de R0/R1 (50k events/mes). Cuando crezcamos a R2+ shadow mode (~10 extracciones × 30 días = 300/mes — bajo) sigue siendo free. R3+ con orquestador podría llegar a ~5k extracciones × N spans cada una = decenas de miles de events/mes — evaluar Pro tier (~USD 50/mes a partir de 50k events).
- **Datos clínicos en servicio externo.** Cada trace incluye el `output_json` completo del extractor — el `ObstetricSummary` con campos como `notes_summary` que pueden incluir información sensible si el PDF la tuvo. Mientras procesemos sólo PDFs sintéticos, esto es aceptable. **Antes de procesar PHI real, hay que decidir si Langfuse Cloud es compatible** (probablemente no sin BAA, ver § Privacidad).
- **Vendor lock-in moderado.** El SDK no es estándar OpenTelemetry — migrar a otro provider (Helicone, Arize, Phoenix, OTel custom) implica rewrite de `tracing.py`. Mitigación: nuestra capa `trace_extraction(...)` es nuestra abstracción; si migramos, solo cambia su implementación.

### Neutral

- **Tabla de pricing necesita maintenance.** Anthropic cambia precios cada 6-12 meses. Sumar un check en CI que valide contra la tabla pública sería ideal pero todavía no implementado — pendiente como TODO en `pricing.py`.

## Privacidad y PHI — CRÍTICO

**Estado actual (R0–R1):** SICA procesa exclusivamente PDFs sintéticos generados con datos ficticios (ver `services/clinical-extractor/data/synthetic_case_*.pdf`). El `output_json` que se envía a Langfuse contiene `ObstetricSummary` con campos clínicos pero **ningún dato de paciente real**. Bajo este régimen, Langfuse Cloud (US) es aceptable.

**Antes de procesar PHI real, hay que evaluar:**

1. **Langfuse Cloud + BAA (Business Associate Agreement).** Si Langfuse ofrece BAA bajo HIPAA o equivalente regional peruano, evaluar firma. Esto autorizaría procesamiento de datos identificables. A 2026-05-26 el sitio público no menciona BAA explícitamente — requiere contacto comercial.
2. **Langfuse self-hosted.** Deploy del open-source de Langfuse en infra controlada (Render, GCP, on-prem partner). Costo de mantenimiento adicional pero datos nunca salen de nuestro perímetro. Probablemente el camino en R2+ si BAA no es viable.
3. **Tracing con `output_json` redactado.** Trazar tokens + latencia + costos pero **omitir el `output_json`** del trace. Pierde la capacidad de inspección visual del output pero preserva las métricas operativas. Implementable con un flag `LANGFUSE_INCLUDE_OUTPUT=false`.
4. **OpenTelemetry custom.** Stream tracing a un destino que sí cumpla compliance (Datadog con BAA, Sentry, o stack local). Implica abandonar Langfuse — recurso de último escenario.

**Trigger explícito para tomar esta decisión:**

- Antes de firmar primer partner clínico con datos reales (issue #4 sin resolver al 2026-05-26).
- Antes de cualquier extracción contra una historia clínica desidentificada del dataset retrospectivo (issue #5).
- Antes de R2 shadow mode (Mes 5+, Oct 2026).

Documentar la decisión final en un ADR superseder (probablemente ADR 0008+).

## Alternatives considered

### Alternativa A: Helicone

**Forma:** Proxy reverso entre el extractor y Anthropic. Toda llamada al modelo pasa por Helicone, que tracea automáticamente sin SDK.

**Por qué no:**
- Ya descartado en **ADR 0003** por razones de seguridad/PHI: ningún proxy externo entre nosotros y el modelo. Aunque Helicone ofrece "edge mode" (no toca el payload), el patrón arquitectónico contradice la política de "datos nunca pasan por intermediario sin contrato explícito".
- Sin proxy, no se obtiene observability automática — quedaría una solución reducida (manual instrumentation) equivalente a lo que hacemos con Langfuse SDK.

### Alternativa B: OpenTelemetry custom + backend genérico

**Forma:** Instrumentar con OTLP, stream a Jaeger / Tempo / Datadog / similar.

**Por qué no en R0:**
- Más control (estándar abierto, swap fácil de backend) pero significativamente más trabajo: definir spans, atributos, exportador, sampling, propagación. Probablemente 2-3 semanas de bootstrap antes de ver el primer trace en un dashboard.
- Backends genéricos no entienden LLM semantics (tokens, costo, prompts) — habría que customizar UI / queries.
- Reservamos OTel para R3+ si Langfuse no escala o si necesitamos cross-service traces fuera del scope LLM (ej. trace que abarque API + extractor + DB).

### Alternativa C: LLM-as-judge sin tracing infra

**Forma:** Confiar 100% en el harness de evaluación (ADR 0005) corriendo en CI + datasets curados. Sin observability en producción.

**Por qué no:**
- El harness mide **calidad** (factual_accuracy, omisiones, hallucinations) contra ground truth. No mide **costo ni latencia** ni captura outputs problemáticos en runs no-evaluados.
- Cuando MedGemma esté disponible, no podemos comparar costo/latencia entre providers sin trazas reales.
- El gate del harness (ADR 0005) y la observability de producción (este ADR) son **complementarios**: el harness es offline pre-merge, Langfuse es online post-merge.

### Alternativa D: Langfuse self-hosted desde el día uno

**Forma:** Deploy local de Langfuse en Render / Docker Compose.

**Por qué no en R0:**
- Otro servicio que mantener (DB de Postgres, S3, ClickHouse). En R0 tenemos exactamente 1 servicio en Render (`sica-api`) — sumar 3 más para hostear Langfuse no se justifica con el volumen actual de traces.
- Self-hosted tiene sentido cuando: a) necesitamos PHI sin BAA, o b) el volumen excede tier free de Cloud y self-hosted sale más barato. Ninguna de las dos aplica en R0/R1.
- Migración Cloud → self-hosted es factible (mismo SDK, solo cambia `LANGFUSE_BASE_URL`). Diferimos el costo.

## Referencias

- **Commit del feature:** `2b53e29` — `feat(extractor): integrate Langfuse SDK for LLM observability (closes #14)`. Trae `settings.py`, `pricing.py`, `tracing.py`, integración en `AnthropicProvider.extract`, 26 tests nuevos (9 pricing + 17 tracing), conftest con fixture autouse de aislamiento.
- **Commit del ADR:** (hash del commit que crea este archivo).
- **Issue cerrado:** [#14](https://github.com/aaronhuaynate66/sica-platform/issues/14) — Setup Langfuse Cloud para observability LLM.
- **Smoke test E2E verificado:** extracción real de `synthetic_case_01.pdf` (2026-05-26 15:36 UTC) → trace `id=6fcf4c62` en `https://us.cloud.langfuse.com` con `metadata.case_id=synthetic_case_01`, 4261 input tokens, 1447 output tokens, ~USD 0.034 costo calculado, 19.5s latencia.
- **Documentación externa:** [Langfuse Python SDK v3 docs](https://langfuse.com/docs/sdk/python/sdk-v3), [Anthropic pricing page](https://www.anthropic.com/pricing).
- **ADRs relacionados:** ADR 0003 (PHI policy — define qué se permite y qué no en R0–R5), ADR 0004 (model routing — Langfuse va a usar `provider_id` para distinguir trazas de cada provider cuando MedGemma esté disponible), ADR 0005 (evaluation methodology — gate offline, complementario a la observability online de este ADR), ADR 0006 (Render config — `LANGFUSE_*` secrets se setean en Render UI igual que `ANTHROPIC_API_KEY`).

## Revisión

Esta decisión se revisa explícitamente en uno de estos triggers:

- **Antes de procesar PHI real.** Bloqueante absoluto — decidir entre BAA / self-hosted / output redacción / OTel custom.
- **Langfuse v4 estable** (probablemente Q3 2026). Evaluar upgrade y actualizar el pin.
- **Volumen mensual > 50k events.** Evaluar Pro tier vs self-hosted vs sampling agresivo.
- **MedGemma 4B operativo** (issue #12). Validar que el dashboard de Langfuse maneja bien la comparación cross-provider.
- **Apps/api o futuro orquestador necesitan tracing propio.** Definir propagación de trace context cross-service.

Hasta entonces, **Langfuse Cloud US con SDK v3.x y sample_rate=1.0** es la configuración de producción.
