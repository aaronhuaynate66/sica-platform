# 0004. Política de routing de modelos AI

- **Status:** Accepted
- **Date:** 2026-05-21
- **Deciders:** Aaron Huaynate (founder / CTO)
- **Tags:** architecture, ai-models, routing, phi, compliance
- **Related:** [ADR 0001](0001-monorepo-turborepo.md) (monorepo), [ADR 0003](0003-security-and-phi-policy.md) (PHI handling), [issue #12](https://github.com/aaronhuaynate66/sica-platform/issues/12) (viabilidad MedGemma 4B — abierto)

## Context

SICA procesa información de salud identificable (PHI) en jurisdicción peruana y opera bajo Ley 29733. Cada operación con PHI debe quedar trazada (modelo + versión + prompt + input). STRATEGY § 11.4 propone una política de routing inicial; este ADR la **formaliza, agrega criterios de evaluación, define triggers de revisión, y especifica audit trail y rollout**.

Por qué se decide ahora:

1. **R0 entra a benchmark.** Sin política de routing no se puede definir qué modelo se evalúa contra qué métrica. STRATEGY § 7 define el gate de salida R0 como "MedGemma 4B ≥85% factualidad, ≤5% omisiones", lo que presupone una decisión de qué corre default.
2. **Múltiples modelos con trade-offs distintos.** MedGemma local (soberanía, latencia mayor, calidad por confirmar), Gemini cloud (calidad alta, latencia baja, PHI a través de frontera), Document AI (OCR especializado), MedSigLIP (encoder visual), Anthropic Claude (asistente de desarrollo). Sin política explícita, la elección queda implícita en cada PR.
3. **Compliance Ley 29733.** El asesor regulatorio y el partner van a preguntar dónde se procesa cada tipo de dato. La respuesta tiene que estar documentada antes de la pregunta.
4. **ADR 0003 ya vetó Anthropic Claude para PHI real en Fase 1.** Este ADR complementa con la otra cara: qué SÍ se usa y bajo qué condiciones.
5. **Estado actual del código (`clinical-extractor`)** usa Claude Sonnet 4.5 porque es lo más rápido para validar mecánica end-to-end. Esa **no es la decisión final** — es decisión de bootstrap, formalmente capturada en issue [#13](https://github.com/aaronhuaynate66/sica-platform/issues/13).

Restricciones que pesan en la decisión:

- **Hardware bootstrap:** STRATEGY § 11.5 ancla el costo a L4 (USD 516/mes 24/7) o A100 puntual (USD 2,682/mes). No hay presupuesto Fase 1 para H100.
- **Datos en frontera:** STRATEGY § 13.6 marca residencia de datos como TODO crítico. Hasta validación legal, asumimos que enviar PHI real a cloud sin política explícita es riesgo regulatorio.
- **Dependencia de #12:** la viabilidad técnica de MedGemma 4B sobre historias clínicas peruanas reales **no está medida todavía**. Los umbrales en Nivel 2 son objetivos derivados de STRATEGY § 12.3, no mediciones empíricas. Se confirman / ajustan cuando #12 cierre con memo técnico.

## Decision

SICA adopta una **política de routing condicional** estructurada en cinco niveles. Los niveles 1-3 cubren la decisión arquitectónica; los niveles 4-5 cubren la operación auditada (audit trail) y el cambio controlado (rollout/versionado).

### Nivel 1 — Default por tarea

| Tarea | Modelo default | Fallback / escalamiento | Latencia esperada (p95) | Razón |
|---|---|---|---:|---|
| Resumen de notas, labs, reportes obstétricos | **MedGemma 4B local** | Gemini 2.5 Flash si contexto >32k tokens y política del workflow lo permite | 3-8s | PHI sensible. Procesamiento local default por STRATEGY § 11.1 + ADR 0003 |
| Extracción estructurada de PDF nativo | **Gemini 2.5 Flash** | MedGemma 4B local | 1-3s | Gemini tiene visión nativa de PDFs (estructura, tablas, figuras). MedGemma 4B no llega a la calidad necesaria sobre PDFs complejos. Cobertura PHI: ver Nivel 4 + ADR 0003 § 7 |
| OCR de PDF escaneado (manuscritos, reportes históricos) | **Document AI (Google)** | Tesseract local | 2-5s | Document AI está optimizado para manuscritos médicos. Trade-off: cruza frontera; aplica política de Nivel 4 + DPA con GCP |
| Retrieval / búsqueda visual (ecografías, reportes con imagen) | **MedSigLIP embeddings** | Sin fallback | 200-500ms | Encoder dedicado, no generación. Bajo riesgo de fuga vía output |
| Razonamiento clínico complejo (handoff largo, brief preanestésico) | **MedGemma 27B text-only** si hardware disponible; **Gemini 2.5 Pro** si no | — | 5-15s | Profundidad > tarea simple. Selección concreta del default depende de resultado de #12 |
| Care gaps / detección de brechas (checklist prenatal, CRED) | **Reglas estructuradas + retrieval híbrido + MedGemma 4B** | — | 1-3s | Tarea estructurada con reglas + razonamiento. Reglas hacen el trabajo deterministico; LLM cierra la parte ambigua |
| **Desarrollo / testing con datos sintéticos o desidentificados** | **Anthropic Claude (Opus/Sonnet)** permitido | — | Variable | Claude asiste el desarrollo (este mismo asistente). Permitido para datos sintéticos o desidentificados según `data-handling.md` § 7. Coherente con ADR 0003 |
| **PHI real** | **Anthropic Claude PROHIBIDO** | Ver default por tarea arriba | — | Veto explícito documentado en ADR 0003. Cambiar este veto requiere ADR nuevo |
| Output con confianza < umbral (ver Nivel 2) | **Abstención obligatoria** | El médico decide sin sugerencia | — | "No encontrado" > "alucinado". STRATEGY § 11.4 última fila; STRATEGY § 11.1 principio 5 |

### Nivel 2 — Criterios de evaluación (umbrales para mantener default)

> **Formalizado en `docs/evaluation/metrics-specification.md` el 2026-05-22.**
> Las definiciones matemáticas exactas de cada métrica (factual accuracy, critical omissions, hallucinations, calibration error) viven ahora en el documento de especificación. Esta tabla es vista operativa por modelo y tarea; la spec es la fuente de verdad sobre **cómo se calcula** cada métrica.
> Decisiones metodológicas (paráfrasis verbatim-casi, criticidad, ground truth dudoso) en [ADR 0005](0005-evaluation-methodology.md).

Estos umbrales determinan si un modelo **mantiene su posición de default** o si dispara un trigger del Nivel 3. Anclados en STRATEGY § 12.3 + § 10 + spec formal.

| Modelo | Tarea | Métrica primaria | Umbral | Métrica secundaria | Umbral | Estado |
|---|---|---|---:|---|---:|---|
| MedGemma 4B | Resumen obstétrico | Factual accuracy (span-level) | ≥85% | Critical omissions | ≤5% | **Objetivo** — confirmar empíricamente en #12 |
| MedGemma 4B | Care gaps | Recall de brechas relevantes | ≥80% | Falsos positivos por sesión | ≤2 | **Objetivo** — confirmar en R2 |
| MedGemma 27B / Gemini 2.5 Pro | Handoff materno-neonatal | Completitud de datos críticos | ≥95% | Correcciones críticas del médico | <10% | **Objetivo** — confirmar en R3 |
| Gemini 2.5 Flash | Extracción PDF nativo | F1 macro campos críticos | ≥0.90 | Latencia p95 | <3s | **Objetivo** — confirmar en R0/R1 |
| Document AI | OCR PDF escaneado | Character accuracy sobre muestra del partner | `[TODO]` — sin baseline empírica todavía | Word accuracy | `[TODO]` | **Pendiente** — establecer baseline con dataset del partner |
| MedSigLIP | Retrieval visual | Recall@5 en query relevantes | `[TODO]` — sin baseline | Latencia p95 | <500ms | **Pendiente** — caso de uso visual entra recién en R3+ |
| Cualquier modelo | Calibración de confianza | Brier score | ≤0.20 | Reliability gap | ≤10% | **Objetivo** — STRATEGY § 10.5 |
| Cualquier modelo | Hallucination en producción | Tasa de evidence pointer fallido | <2% del output | — | — | **Objetivo** — STRATEGY § 10.5 |
| Cualquier modelo | Aceptación del médico | Tasa de outputs aceptados sin corrección crítica | ≥60% (R2 baseline) → ≥75% (R3+) | — | — | **Objetivo** — STRATEGY § 12.3 + § 14.5 |

**Umbrales marcados `[TODO]`:** no se inventan. Quedan abiertos hasta que el benchmark correspondiente produzca baseline empírica. Hasta entonces, el modelo opera en modo shadow o asistivo no mandatorio.

### Nivel 3 — Triggers de revisión

Eventos que disparan reevaluación inmediata de esta política. Cada trigger tiene **consecuencia explícita** — no se queda en "lo discutimos".

1. **MedGemma 4B no alcanza ≥85% factualidad** sobre dataset retrospectivo del partner en evaluación R0 → Escribir ADR nuevo evaluando opciones: (a) fine-tuning con datos peruanos, (b) subir default a MedGemma 27B text-only, (c) cambiar default a Gemini cloud con políticas reforzadas y DPA actualizado.
2. **Latencia p95 local > 8 segundos** en operación normal (no en cold start) → Revisar configuración GPU (¿L4 está saturado? ¿A100 puntual?). Si infra no soluciona, evaluar Gemini para esa tarea.
3. **Costo mensual de cómputo > USD 2,000** sin crecimiento proporcional en valor medido (consultas procesadas + adopción) → Revisar. Ancla en STRATEGY § 11.5 (USD 516 L4 vs USD 2,682 A100): cruzar USD 2,000 implica salto de infraestructura que requiere justificación.
4. **Google deprecia MedGemma o cambia licencia open-weight** → Revisar urgente. STRATEGY § 18 lista lock-in de IA como riesgo. Sin MedGemma open-weight, la apuesta local cambia.
5. **Aparece modelo médico open-weight superior** (MedGemma 3, BioMedLM-X, modelo médico en español) → Evaluar migración. No urgente, pero sí revisar dentro de 30 días del release.
6. **Partner exige residencia específica de datos** que cambie las premisas (p. ej. "ningún dato cruza frontera ni con DPA") → Revisar urgente. Implica eliminar Gemini/Document AI de tareas con PHI o operación local-only.
7. **Regulación peruana cambia sobre residencia de datos o uso de modelos cloud** (modificación de Ley 29733, reglamento, directiva ANPD) → Revisar urgente.
8. **Costo de Gemini API sube >50%** o aparecen límites de cuota que afectan operación → Evaluar incremento de uso local o cambio de proveedor cloud. Presupuesto cloud de STRATEGY § 15.4 es USD 22,000 / 18 meses — un alza de 50% lo rompe.
9. **Modelo cloud (Gemini) muestra >2% degradación en regression tests trimestrales** sobre la eval suite (STRATEGY § 10.6) → Revisar el modelo o su versión específica.
10. **Confidence calibration drift detectado en producción** (sistema reporta alta confianza pero outputs son malos según feedback del médico) → Revisar urgente. STRATEGY § 10.5.
11. **Hardware GPU local no disponible en infraestructura del partner** (clínica no acepta hardware on-prem, sin GPU en datacenter compartido) → Evaluar alternativas cloud regionales con políticas reforzadas.
12. **Más de 1 incidente S1/S2 relacionado con un modelo específico** en 6 meses → Revisar política sobre ese modelo. Coherente con `incident-response.md`.

### Nivel 4 — Audit trail por operación

Cada inferencia clínica (no incluye eval suite ni desarrollo) queda registrada con el siguiente schema mínimo. Coherente con criterio (e) del issue #13 y con STRATEGY § 11.1 principio 4.

```
operation_id            UUID         identificador único de la operación
timestamp_utc           ISO 8601     momento de la inferencia (servidor)
workflow                string       resumen | extraccion_pdf | ocr | handoff | brief_anestesia | care_gaps
model_provider          string       medgemma_local | gemini | document_ai | medsiglip | claude | tesseract
model_id                string       p. ej. medgemma-4b, gemini-2.5-flash, document-ai-v1
model_version           string       hash o versión declarada por el proveedor
prompt_id               string       referencia al prompt_registry (versión semántica)
prompt_hash             string       SHA-256 del prompt efectivo enviado (system + user template + variables resueltas)
input_hash              string       SHA-256 del input clínico (PHI). El contenido NO se loggea, sólo el hash
input_size_tokens       int          tamaño del input medido en tokens
input_modality          string       text | pdf_nativo | pdf_escaneado | imagen | mixto
output_hash             string       SHA-256 del output generado
output_size_tokens      int          tamaño del output
confidence_score        float        score declarado por el modelo o por capa de calibración
abstained               boolean      true si el sistema decidió no producir output (Nivel 1)
abstention_reason       string|null  razón de abstención (low_confidence | out_of_distribution | policy | ...)
latency_ms              int          latencia end-to-end de la inferencia
escalated_from          string|null  modelo previo si hubo escalamiento (p. ej. medgemma_local → gemini_flash)
escalation_reason       string|null  context_overflow | low_confidence | timeout | error
actor_id                string       identidad del usuario humano (médico) que disparó la operación
actor_role              string       rol RBAC del actor
tenant_id               string       partner / sede en multi-tenant
patient_pseudo_id       string       identificador opaco del paciente (no DNI, no HC real)
encounter_pseudo_id     string       identificador opaco del encuentro
acceptance_status       string|null  accepted | edited | rejected | pending (llenado cuando el médico revisa)
acceptance_categories   string[]     factual_fix | critical_addition | style | emphasis | removal (STRATEGY § 10.3)
acceptance_timestamp    ISO 8601     cuándo el médico revisó
```

**Reglas operativas del audit trail:**

- El **contenido de PHI nunca se loggea**, sólo hashes. La trazabilidad opera sobre identificadores opacos.
- Cada operación clínica produce **exactamente un registro** de audit trail. Re-inferencias o reintentos generan registros nuevos vinculados por `operation_id` parent.
- Audit logs son **append-only**, almacenados separados del sistema operacional (ver `data-handling.md` § 4.4).
- Retención mínima: 5 años (`data-handling.md` § 5.1), sujeto a confirmación con asesor legal sobre Ley 29733 + Ley 30024.
- `acceptance_status` y `acceptance_categories` alimentan los loops 1 y 2 del Data Flywheel (STRATEGY § 9.1).

Schema de implementación concreto (tipos exactos en Postgres/Avro, índices, partitioning) queda como **detalle de ejecución de R0**, no parte de este ADR.

### Nivel 5 — Política de versionado y rollout

Cómo se cambia un modelo en producción sin romper trazabilidad ni introducir regresiones silenciosas. Coherente con criterio (f) del issue #13 y con STRATEGY § 10.2 / § 10.6.

**5.1 Versionado del modelo.** Cada modelo en uso declara `(model_id, model_version)`. Cuando el proveedor publica una versión nueva (p. ej. Gemini 2.5 Flash → 2.5 Flash v2):

1. **No se adopta automáticamente.** El sistema queda fijo en la versión actual hasta evaluación.
2. La eval suite completa corre contra la versión nueva en entorno aislado.
3. Si todas las métricas primarias se mantienen dentro de ±2% y no hay degradación en métricas críticas, se aprueba para shadow rollout.

**5.2 Shadow rollout.** Antes de promover una versión nueva (o un modelo nuevo) a default:

1. El modelo nuevo corre **en paralelo** al actual durante un periodo mínimo de 2 semanas en condiciones reales.
2. El output del modelo nuevo se loggea y compara contra el actual, pero **no se muestra al médico**.
3. Métricas comparadas: factualidad, omisiones, latencia, abstención, costo, divergencia entre outputs.
4. Si el modelo nuevo iguala o supera al actual en todas las métricas primarias durante 2 semanas, se promueve.

**5.3 Promoción gradual (canary).** Promoción no es flip global:

1. **5% del tráfico** durante 3 días → métricas estables → continúa.
2. **25% durante 5 días** → métricas estables + sin reporte de incidente clínico → continúa.
3. **100%** después de validación.

En cualquier paso, métricas que degraden disparan rollback automático al modelo previo. La degradación se mide vs. ventana de control de los últimos 14 días.

**5.4 Métricas que disparan rollback automático.**

| Métrica | Umbral de rollback | Ventana de medición |
|---|---|---|
| Factualidad degradada vs. baseline | >3 puntos porcentuales abajo | Últimas 200 inferencias o 24h, lo que ocurra primero |
| Omisiones críticas | >2 puntos porcentuales arriba | Últimas 200 inferencias o 24h |
| Tasa de abstención | Cambia >50% relativo en cualquier dirección | Últimas 200 inferencias o 24h |
| Latencia p95 | >50% arriba de baseline | Ventana de 1 hora |
| Tasa de error/timeout | >5% del tráfico | Ventana de 15 minutos |
| Costo por inferencia | >100% arriba de baseline (si modelo cloud) | Ventana diaria |
| Reporte de incidente clínico S1/S2 atribuible al modelo nuevo | 1 (cero tolerancia) | Inmediato |

**5.5 Rollback manual.** El founder, líder clínico o IC durante un incidente puede ejecutar rollback manual en cualquier momento. La acción queda en audit log con razón documentada.

**5.6 Documentación del cambio.** Cada promoción de modelo a default queda registrada en:

- Commit del cambio de configuración (con referencia a evals corridas).
- Entrada en `MASTER_PLAN.md` (auto-generado vía ADR 0002).
- Si el cambio es ruptura (cambio de proveedor, cambio de default mayor), requiere **ADR nuevo que supersede a este 0004**.

## Consequences

### Positive

- **Routing explícito, no implícito.** Cualquier ingeniero o asesor puede preguntar "qué modelo procesa esto" y obtener respuesta documentada en lugar de leer código.
- **Política auditable** para asesor regulatorio y partner (insumo para el DPA pendiente, coherente con `ley-29733-compliance.md`).
- **Criterios objetivos para cambiar de modelo.** Nivel 2 + Nivel 3 quitan la decisión del "me parece" y la ponen en métricas + triggers.
- **Múltiples proveedores reducen lock-in.** STRATEGY § 18 lista lock-in de IA como riesgo; este ADR lo mitiga con capa de abstracción y triggers de migración.
- **PHI nunca toca proveedor cloud genérico** sin política explícita. Consistente con ADR 0003.
- **Costo predecible** para la parte local: MedGemma sobre GPU dedicada es costo fijo, no escala con uso unitario.
- **Audit trail completo** (Nivel 4) — base regulatoria sólida y dato útil para los loops 1, 2, 3 del Data Flywheel (STRATEGY § 9).
- **Rollout controlado** (Nivel 5) reduce riesgo de degradación silenciosa al cambiar versiones de modelo. Sin esto, una actualización de Gemini puede romper resúmenes obstétricos sin que nadie lo note hasta que un médico se queje.

### Negative

- **Mantener infra MedGemma local requiere expertise MLOps** que el equipo Fase 1 no tiene full-time. Mitigación: STRATEGY § 19.2 prevé MLOps engineer mes 12+.
- **Latencia local mayor** que cloud (3-8s local vs 1-3s cloud). Aceptable para resumen pre-consulta; potencialmente problemático para brief preanestésico urgente. Trigger 2 mitiga si se materializa.
- **Calidad de MedGemma 4B probablemente por debajo de modelos frontera.** A confirmar en #12. Si se confirma, trigger 1 dispara reevaluación.
- **Complejidad operativa** de orquestar múltiples modelos + audit trail + shadow rollout. Mitigación: orquestador centralizado (LangGraph + FastAPI según STRATEGY § 11.3) absorbe la complejidad detrás de una API interna estable.
- **Eval suite contra cada modelo configurado** consume tiempo de CI y costo de inferencia. Mitigación: subset rápido en cada PR + suite completa pre-deploy (STRATEGY § 10.7).
- **Posible degradación silenciosa** si la calibración de confianza se descalibra y nadie lo detecta. Mitigación: trigger 10 + métricas de Nivel 5.4 disparan revisión.
- **Umbrales del Nivel 2 son aspiracionales** hasta #12. Riesgo: si los datos empíricos muestran que MedGemma 4B no llega a 85% factualidad, hay que reescribir buena parte de la decisión. Aceptado deliberadamente; la alternativa (no escribir ADR hasta #12) bloquea el resto del trabajo de R0.

## Alternatives considered

### Alternativa A: Sólo cloud (Gemini default + Claude para desarrollo)

**Forma:** Gemini cloud procesa todo, incluso PHI; Claude sólo para asistencia de desarrollo.

**Por qué no:**
- Dependencia total de un proveedor (lock-in de IA en su forma extrema).
- Costo escala con uso por consulta. Sin techo de costo unitario en infraestructura propia.
- PHI cruza frontera siempre. Requiere DPA reforzado, validación de residencia de datos, política de excepciones para cada cliente que pida residencia local.
- Conflicto potencial con políticas hospitalarias peruanas de residencia que el partner fundador puede tener.
- Si la regulación peruana endurece (Trigger 7), no hay path de migración rápido — la arquitectura entera está cloud-bound.
- **Descartada porque:** el riesgo regulatorio peruano es no trivial y el costo de migrar de cloud a local en producción es alto. Mejor diseñar local-first desde día uno aunque cueste DevOps.

### Alternativa B: Sólo local (MedGemma 4B + 27B sin cloud)

**Forma:** todo procesamiento on-prem o en GPU controlada por SICA. Sin Gemini, sin Document AI, sin Claude.

**Por qué no:**
- Algunas tareas requieren capacidades que MedGemma no tiene: PDF nativo con tablas (Gemini lo lee, MedGemma 4B no), OCR de manuscritos médicos (Document AI > Tesseract en este dominio).
- Sin acceso a modelos frontera para casos de razonamiento extremo (handoff complejo con múltiples comorbilidades, brief preanestésico de cesárea de emergencia con datos críticos).
- Sin Claude para desarrollo: el equipo pierde ~30-50% de velocidad de iteración. STRATEGY § 19.4 explícitamente abraza operación AI-native; quitarlo en desarrollo es autosabotaje sin ganancia regulatoria.
- **Descartada porque:** híbrido controlado (local para PHI default, cloud puntual con política) captura las ventajas de ambos sin los contras totales de ninguno.

### Alternativa C: Anthropic Claude como default incluido PHI

**Forma:** Claude opera tanto en desarrollo como en producción sobre PHI real.

**Por qué no:**
- **ADR 0003 ya documentó este veto** con justificación operacional (Claude es asistente de desarrollo Y proveedor cloud → separación de entornos comprometida) y regulatoria (sin DPA peruano específico vigente).
- Levantar el veto requiere ADR nuevo, no puede hacerse silenciosamente vía este ADR.
- **Descartada porque:** ADR 0003 es vinculante. Este ADR lo respeta.

### Alternativa D: Modelos open-source genéricos (Llama, Mistral) sin especialización médica

**Forma:** sustituir MedGemma por Llama 3 o Mistral con prompts especializados.

**Por qué no:**
- MedGemma fue entrenado con datos clínicos médicos. La especialización rinde frutos medibles (Google publicó benchmarks). Llama / Mistral son generalistas; los prompts no compensan tuning de pretraining.
- Comunidad open-source más grande no es ventaja cuando lo que se necesita es performance médica específica.
- Si MedGemma 4B no rinde, las alternativas serias son (a) MedGemma 27B, (b) fine-tuning local de un open-source médico, (c) Gemini cloud — no Llama generalista.
- **Descartada porque:** la especialización médica es valor real, no marketing.

### Alternativa E: Routing dinámico aprendido (modelo aprende qué modelo usar)

**Forma:** un meta-modelo decide en runtime cuál de los modelos disponibles llamar, basado en el input.

**Por qué no:**
- Complejidad muy alta para Fase 1.
- Requiere volumen de datos que SICA no tiene aún.
- Hace el comportamiento menos predecible y menos auditable (clave en contexto regulatorio).
- La política por tarea (Nivel 1) ya captura la mayor parte del valor con muchísima menos complejidad.
- **Descartada porque:** sobreingenierizado para el problema actual. Se puede evaluar en R5+ si aparece evidencia de que el routing estático es subóptimo.

## References

- `STRATEGY.md` § 6 (capacidades core), § 9 (Data Flywheel), § 10 (Eval Infrastructure), § 11.1 (principios), § 11.4 (tabla original), § 11.5 (costos GPU), § 12.3 (umbrales clínicos), § 18 (riesgos).
- [ADR 0001](0001-monorepo-turborepo.md) — Monorepo con Turborepo + pnpm.
- [ADR 0003](0003-security-and-phi-policy.md) — Security and PHI handling policy (veto Claude para PHI real).
- `docs/security/data-handling.md` § 7 — Modelos AI y PHI (tabla complementaria de esta política).
- `docs/security/incident-response.md` — Procedimiento de respuesta a incidentes con un modelo.
- [GitHub issue #12](https://github.com/aaronhuaynate66/sica-platform/issues/12) — Viabilidad MedGemma 4B (dependencia abierta).
- [GitHub issue #13](https://github.com/aaronhuaynate66/sica-platform/issues/13) — Este ADR responde a este issue.
- Google MedGemma (open-weight): `[TODO — confirmar URL canónica al momento de release; Google ha movido el ecosistema entre repos]`.
- Google MedSigLIP — papers Google Research.
- Anthropic Claude API documentation.
- Google Gemini API documentation.
- Google Cloud Document AI documentation.
- Ley 29733 Perú (vía ADR 0003) y reglamento.
- IMDRF — principios de validación clínica de software.

## Migration log

| Fecha | Cambio | Autor | ADR superseder |
|---|---|---|---|
| 2026-05-21 | Creación inicial. Umbrales del Nivel 2 marcados como objetivos hasta cierre de #12. | Aaron Huaynate | — |
| 2026-05-22 | Nivel 2 ahora referencia `docs/evaluation/metrics-specification.md` como fuente de verdad de las definiciones matemáticas de las métricas. Decisiones metodológicas movidas a ADR 0005. Sin cambio funcional de umbrales. | Aaron Huaynate | — |

`[TODO — revisión clínica/regulatoria firmada]` — El issue #13 lista como criterio de cierre "Revisión por al menos un asesor clínico/regulatorio firmada en el PR del ADR". Esta firma queda **pendiente** y debe completarse antes de que el ADR pase de policy interna a documento expuesto a partner. Cuando se obtenga, registrar en este log la fecha y firmante.
