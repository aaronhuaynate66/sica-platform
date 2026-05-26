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

## Actualización 2026-05-26 — Trace context propagation (apps/api → extractor)

Implementada la propagación de `trace_id` desde el endpoint `POST /extract` de `apps/api` hacia el `clinical-extractor`, materializando uno de los triggers de revisión documentados arriba (*"Apps/api o futuro orquestador necesitan tracing propio"*).

### Antes

`apps/api` → `extractor` → 2 traces top-level **separadas** en el dashboard:

- `api_extract_request` (sin observations) — creada por `apps/api`, mostraba latencia HTTP pero no el detalle del LLM call.
- `extract_<case_id>` (1 generation, sin span padre) — creada por el extractor, mostraba el LLM call pero sin contexto del request HTTP.

Visualmente: 2 entradas separadas en el dashboard, difícil correlacionar una con la otra. Para debuggear "este request fue lento", había que cruzar timestamps a mano.

### Después

`apps/api` → `extractor` → **1 trace** con jerarquía padre-hijo. Estructura observada en el smoke E2E (2026-05-26 16:10 UTC):

```
TRACE fa8cca2e  name=extract_<case_id>
  metadata: request_id=7937b8eb, service=sica-api, endpoint=POST /extract
  observations (2):
    SPAN       name=api_extract_request          id=e6934dfb  parent=ROOT
    GENERATION name=extract_<case_id>            id=80275b0c  parent=e6934dfb
               model=claude-sonnet-4-5-20250929
```

Visualmente: 1 entrada en el dashboard con expansión jerárquica. Click en el trace muestra:

- **SPAN root** `api_extract_request` (latencia HTTP total, request_id, pdf_filename, pdf_size_bytes en metadata).
- **GENERATION child** `extract_<case_id>` (latencia del extractor, tokens, costo USD, model, output_json del extractor).

### Implementación

**`apps/api` (commit `b70538d`)**:

- Nuevo módulo `sica_api.tracing` con `start_extract_trace()` y `finish_extract_trace()`.
- `start_extract_trace` crea un `span` root via `client.start_observation(as_type="span", name="api_extract_request", metadata={...})`. Devuelve `{trace_id, span_id, span, request_id}`.
- `routes/extract.py` invoca `start_extract_trace` antes del extractor y pasa `parent_trace_id` + `parent_span_id` como kwargs.
- En path exitoso: `finish_extract_trace(success=True, output_summary={...sin PHI...})` actualiza el span con outcome y latencia.
- En path de error: `finish_extract_trace(success=False, error=str(exc))` antes de devolver 500.
- **Output summary del span padre intencionalmente reducido**: contiene `confidence_score`, `num_evidence_spans`, `num_active_problems`, `num_lab_results`, `uploaded_filename`, `size_bytes`. NO incluye `notes_summary`, `lab_results[].value`, ni campos clínicos completos. El detalle clínico vive en el `output_json` de la generation child (creado por el extractor). Esto limita la superficie de PHI cuando se vincule a usuarios reales.

**`clinical-extractor` (commit `d160aec`)**:

- `ExtractionRequest` agrega 2 campos opcionales: `parent_trace_id: str | None` y `parent_span_id: str | None`.
- `clinical_extractor.tracing.trace_extraction` acepta los mismos kwargs y construye `trace_context: TraceContext = {"trace_id": ..., "parent_span_id": ...}` (omite `parent_span_id` si es None). Pasa el `trace_context` a `client.start_observation`. El SDK enchufa la generation bajo el trace existente.
- `AnthropicProvider.extract` propaga `request.parent_trace_id` y `request.parent_span_id` a `_safe_trace` en ambos paths (success y error).
- `extract_from_pdf` acepta los kwargs y los propaga al `ExtractionRequest`. Default `None` mantiene retrocompatibilidad — código que no pase parent_trace_id ve el comportamiento original (trace top-level propio).

### API de Langfuse v3 — qué SÍ se usa y qué NO

Decisión sutil sobre qué llamadas del SDK invocar:

- **`client.trace()`** — método del SDK v1/v2 que el prompt original sugería. **NO existe en v3**. Reemplazado por `start_observation(as_type="span"|"generation"|...)`.
- **`client.start_observation(as_type="span")`** — usado por `apps/api` para el root.
- **`client.start_observation(as_type="generation", trace_context={...})`** — usado por el extractor para anidar bajo el span del API.
- **`client.start_generation()`** — todavía en v3 pero **deprecated** (será removido en v4). Evitamos.
- **`TraceContext`** — TypedDict definido en `langfuse.types`. Shape: `{"trace_id": str, "parent_span_id": str (NotRequired)}`.

### Beneficios concretos

- **Debugging end-to-end**: en el dashboard, click en una trace muestra el árbol completo HTTP → LLM. Sin saltar entre vistas.
- **Latencia network medible**: `(span.latency - generation.latency)` da la latencia de network/overhead entre `apps/api` y Anthropic. Hoy es subóptima (~6-7s en el smoke) — telemetría que antes no existía.
- **Distinción de timeout**: si un request falla, ahora podemos ver si fue timeout del LLM (generation con duration > timeout_seconds) o timeout del HTTP (span sin generation visible).
- **Future-proof para multi-provider**: con MedGemma operativo, un único request puede llamar a Claude Y MedGemma como 2 generation children del mismo span padre. El dashboard ya soporta esta jerarquía sin cambios adicionales.
- **Output summary sin PHI**: el span padre (visible primero en el dashboard) lleva metadata operacional segura. El generation child con detalle clínico sigue siendo el único lugar donde está el `output_json` completo — y será el primero en redactar / hostear self-hosted cuando se procese PHI real.

### Limitación conocida

El `case_id` del extractor se deriva del `pdf_path.stem` que en producción es el **tempfile** que crea `apps/api` (e.g. `sica-api-qiubyhjd`), no el filename original del upload. Como resultado, en el dashboard la generation tiene `case_id=sica-api-qiubyhjd` en vez de `case_id=synthetic_case_01`. El filename original SÍ está en `metadata.uploaded_filename` del span padre — recuperable, pero no es el campo principal de la generation. **TODO menor:** propagar el filename original como `case_id` explícito desde `apps/api` (vía un nuevo kwarg `case_id` en `extract_from_pdf` que override el derivado del path). No bloqueante.

### Smoke test verificado

- **Comando**: `POST http://127.0.0.1:8765/extract` con `synthetic_case_01.pdf`.
- **Response**: HTTP 200 en 18.6s, JSON válido (`patient_age=32, gestational_age_weeks=28.3, confidence_score=0.95`).
- **Costo Anthropic**: ~USD 0.04 (consistente con smoke previo).
- **Trace en Langfuse**: `id=fa8cca2e`, 2 observations, jerarquía padre-hijo confirmada via API pública (`GET /api/public/traces/{id}`).

### Tests

- **apps/api**: 67/67 pasando. 22 nuevos (15 en `test_tracing.py` + 7 en `test_extract_with_tracing.py`).
- **clinical-extractor**: 85/85 pasando. 4 nuevos en `test_tracing.py` (parent_id propagation).
- Ruff clean en ambos. Mypy clean en ambos.

### Commits asociados

- `b70538d` — feat(api): add Langfuse tracing to POST /extract endpoint
- `d160aec` — feat(extractor): support parent_trace_id for hierarchical traces
- `6e6a745` — docs(adr): update ADR-0007 with trace context propagation

## Actualización 2026-05-26 — Cold start race condition en Render free tier

Después del deploy a producción de los commits `b70538d` y `d160aec`, el smoke test reveló un comportamiento bifurcado dependiendo del estado del container Render. La extracción funciona en ambos casos, pero la entrega de las observations al dashboard de Langfuse depende del timing del container.

### Warm requests (container ya despierto)

- Trace top-level + SPAN root + GENERATION child **llegan completos** al dashboard.
- Jerarquía padre-hijo visible (`parent_id` del GENERATION apunta al `id` del SPAN).
- Verificado con trace `bfc9cc3d` (`env=production`, `request_id=3035ebbf`, 2026-05-26T18:30:44Z): 2 observations correctamente anidadas, `usage.input=4261, usage.output=1251`.

### Cold start requests (después de >15 min idle)

- Trace top-level **sí llega** al dashboard (1 HTTP call inmediato del SDK con la metadata).
- SPAN + GENERATION **se pierden** — el batch async no completa antes de que el container se suspenda post-response.
- Verificado con traces `7e701353` y `c32e7ef0`: `observations=0` en ambas, **incluso 2 horas después** del request. No es delay, son perdidas.

### Causa

- Langfuse SDK v3 usa **batching async** + background thread para flush — diseñado para no bloquear el response HTTP. Las observations se acumulan en una cola en memoria y se envían en batches.
- Render free tier **suspende el container** después del HTTP response cuando no hay tráfico activo. El proceso Python se pausa o termina sin garantizar drain de threads background.
- Background thread interrumpido antes de drenar la cola → observations se quedan en memoria del container suspendido y nunca llegan al backend.
- Es un **trade-off conocido** del SDK: batching async favorece latencia del request principal, perjudica entornos ephemeral donde el container no garantiza tiempo post-response.

### Estado: TODO no bloqueante

**Cuándo aplica el problema:**

- **Free tier de Render** (containers ephemeral, suspensión post-response).
- **Vercel serverless functions** (similar — function instance termina al return).
- **AWS Lambda** y similares (mismo patrón).
- Cualquier entorno donde el container suspende post-response.

**Por qué no es urgente en R0:**

- No hay tráfico real todavía — sólo smoke tests manuales del founder.
- Cold start ocurre solo en primer request después de >15 min idle. Con tráfico real (1+ request por min), el container queda warm permanentemente.
- En R1+ shadow mode con sesiones de revisión clínica regulares (≥5 PDFs/día concentrados), el container estará warm prácticamente siempre.
- La solución está identificada y queda prompted para implementar cuando sea necesario — no requiere investigación adicional, sólo aplicar el patrón documentado abajo.

### Fix planificado (R1)

Cuando R1 traiga tráfico real y la pérdida de cold-start traces se vuelva visible:

- **Agregar flush sincrónico (bloqueante)** al final de `POST /extract` antes del response HTTP. Reemplaza el flush async del SDK por uno que espere a que la cola esté drenada.
- **`client.flush()` síncrono** llamado explícitamente en `apps/api/src/sica_api/tracing.py::finish_extract_trace`, dentro del mismo try/except que envuelve `span.end()`.
- **También en el extractor** (`clinical_extractor/tracing.py::trace_extraction`) para drenar su cliente al final de la generation. El SDK actualmente sólo dispara un flush async — necesitamos forzar bloqueante.
- **Costo:** +200-500ms latencia por request (el bloqueo dura lo que tarde el HTTP request del SDK al backend de Langfuse).
- **Beneficio:** 100% delivery garantizada, sin pérdida por cold-start.

El prompt completo del fix (qué archivos tocar, qué tests agregar, dónde poner el `client.flush()` exacto) está documentado en las notas de sesión del 2026-05-26. Una sesión `feat(observability): force sync flush for cold-start resilience` debería ser ~20 min.

### Lecciones aprendidas

7. **Observability sobre observability**: bugs en el sistema de tracing son difíciles porque silenciosamente fallan (try/except absorbe errores por diseño). El smoke test del feature pasó en local (warm container), pero falló parcialmente en producción (cold start) sin generar logs ni excepciones visibles. **Regla nueva:** después de deployar cambios de tracing, validar contra producción tanto en path warm como cold (esperar 15+ min y reintentar). No bastar con un solo curl exitoso.

8. **Render free tier no es serverless puro pero comparte el problema**: aunque Render es nominalmente "long-running containers", el free tier los suspende post-response cuando no hay tráfico, replicando la semántica de serverless ephemeral. Cualquier librería que asuma "el proceso vive más allá del response" — SDK con flush async, log aggregators con buffer, métricas via push — sufre el mismo síntoma. **Regla operativa:** cuando se introduzca una nueva dependencia con buffer/batch async en `apps/api`, validar explícitamente que entrega bajo cold-start. Documentar fallback síncrono en el ADR correspondiente.

## Actualización 2026-05-26 — Default environment cambiado a `development`

Tras varios días corriendo, la inspección del dashboard de Langfuse reveló **contaminación cruzada entre entornos**: traces generadas por smoke tests locales (CLI `clinical-extractor extract`, pytest sin fixture aislante, scripts ad-hoc) aparecían con `environment=production`, mezcladas con traces reales del API en Render.

### Causa raíz

El campo `LangfuseSettings.tracing_environment` (en `clinical_extractor/settings.py` y `apps/api/settings.py`) tenía como default `"production"`. Cualquier proceso que importara el SDK SIN setear explícitamente `LANGFUSE_TRACING_ENVIRONMENT` heredaba ese default → traces locales etiquetadas como `production`.

Esto era **fail-open**: el comportamiento más peligroso (contaminar el entorno crítico) era el comportamiento por default.

### Cambio

Default cambiado a `"development"` en ambos módulos:

- `services/clinical-extractor/src/clinical_extractor/settings.py::LangfuseSettings.tracing_environment`
- `apps/api/src/sica_api/settings.py::Settings.langfuse_tracing_environment`

Ahora el default es **fail-safe**:

- **Local dev sin env var explícita** → traces caen en dashboard `development` (segregado).
- **CI sin override** → mismo: `development`.
- **Render production**: setea `LANGFUSE_TRACING_ENVIRONMENT=production` explícitamente en sus Environment vars → override respetado, traces caen en dashboard `production` correctamente.

### Cómo verificar

- **Local**: arrancar `clinical-extractor extract` sin tocar nada, ver que el trace en Langfuse aparece con `environment=development`.
- **Producción**: smoke contra `POST https://sica-api-d1gq.onrender.com/extract` debe seguir generando traces con `environment=production` (override de Render UI prevalece).

### Tests que congelan el contrato

Cuatro tests nuevos (2 por paquete):

- `services/clinical-extractor/tests/test_tracing.py::TestLangfuseSettings::test_environment_defaults_to_development`
- `services/clinical-extractor/tests/test_tracing.py::TestLangfuseSettings::test_environment_can_be_overridden_to_production`
- `apps/api/tests/test_settings.py::test_langfuse_tracing_environment_defaults_to_development`
- `apps/api/tests/test_settings.py::test_langfuse_tracing_environment_overridable_to_production`

Si en el futuro alguien intenta volver el default a `"production"` "por consistencia", estos tests rompen en CI y forzan re-justificación.

### Cleanup retroactivo

Mismo día se ejecutó un cleanup del dashboard borrando 6 traces de smoke tests locales que habían quedado etiquetadas como `production` por el bug. Quedaron en el dashboard 6 traces legítimas (todas con `api_extract_request` como root span — vienen del API real, no del CLI directo).

### Pre-requisito de deploy

**Antes de hacer redeploy** con este cambio, verificar en **Render → service `sica-api` → Settings → Environment** que la var `LANGFUSE_TRACING_ENVIRONMENT=production` esté seteada. Sin esa env var, después del próximo deploy las traces reales del API caerían en `development` (no es data loss, pero el dashboard quedaría dividido raramente).

Históricamente (sesión #14 cuando se configuraron las creds de Langfuse) la var **debería** estar seteada en Render. Si no lo está, agregarla manualmente desde la UI con valor `production` y trigger deploy.
