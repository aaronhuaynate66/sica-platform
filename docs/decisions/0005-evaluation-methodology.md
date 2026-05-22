# 0005. Decisiones metodológicas de evaluación clínica

- **Status:** Accepted
- **Date:** 2026-05-22
- **Deciders:** Aaron Huaynate (founder / CTO)
- **Tags:** evaluation, methodology, factuality, ground-truth
- **Related:** [ADR 0004](0004-model-routing-policy.md) (routing y umbrales por modelo), [issue #11](https://github.com/aaronhuaynate66/sica-platform/issues/11) (definir métricas de factualidad)

## Context

El issue #11 pide formalizar las métricas de factualidad de SICA. Al hacerlo aparecen tres decisiones metodológicas no triviales que no son obvias del schema ni del código:

1. **¿Cómo se trata una "paráfrasis verbatim-casi"?** El extractor a veces produce strings que son casi-literales del PDF pero con cambios menores (capitalización, espacios, sinónimos). ¿Eso cuenta como `exact`, `fuzzy`, o `mismatch`? ¿Cuál es el threshold? ¿Es el mismo para todos los campos?
2. **¿Qué define "crítico"?** El gate de R0 habla de "omisiones críticas". `CRITICAL_FIELDS` está hardcoded en `field_comparator.py`. ¿Sobre qué base se decidieron esos campos? ¿Qué proceso aprueba agregar o quitar uno?
3. **¿Qué pasa cuando el ground truth tiene dudas?** Si el dataset del partner llega con un caso donde A y B (revisores) no acuerdan y el árbitro tampoco está seguro, ¿se incluye el caso en la suite con ground truth probabilístico? ¿Se excluye? ¿Se etiqueta especial?

Cada decisión cambia la interpretación de las métricas y, peor, **cambiarlas tarde invalida baselines históricos**. Por eso van en ADR y no en código comentado.

Este ADR es referenciado por `docs/evaluation/metrics-specification.md` § respectiva en cada decisión.

## Decision

### Decisión 1 — Paráfrasis verbatim-casi se trata como `fuzzy` con threshold provisional 0.6

**Regla:** dos strings se consideran equivalentes si:

- Son iguales tras normalización (lowercase + strip whitespace + colapsar espacios internos) → `match_type = exact`.
- Caso contrario, `difflib.SequenceMatcher(None, a_norm, b_norm).ratio() ≥ FUZZY_RATIO_THRESHOLD` → `match_type = fuzzy`.
- Caso contrario → `match_type = mismatch` (no match).

**Threshold `FUZZY_RATIO_THRESHOLD = 0.6`.** Aplica uniformemente a todos los campos string (no numéricos ni de fecha).

**Por qué 0.6 y no 0.85 (más estricto) ni 0.4 (más laxo).**

- Calibrado contra `synthetic_case_01`. Con 0.85 falla `"Anemia leve"` vs `"Anemia leve gestacional"` (ratio 0.73), que clínicamente es la **misma** condición con calificador. Con 0.4 acepta `"Hipertensión"` vs `"Diabetes"` (ratio ~0.2) — clínicamente distintas. 0.6 separa los dos casos correctamente.
- Coherente con benchmarks de comparación clínica que usan ratios 0.5–0.7 sobre nombres de condiciones.

**Limitaciones explícitas.**

- `difflib.SequenceMatcher` es comparación lexicográfica, **no semántica**. "Anemia" y "anemia gestacional" matchean; "Anemia" y "deficiencia de hierro" (sinónimos clínicos) no.
- TODO crítico: migrar a similitud por embeddings (`sentence-transformers` con modelo médico, o MedSigLIP cuando aplique) cuando exista runtime local. Mientras tanto, 0.6 es **estimación operativa**, no decisión definitiva.

**Revalidación.** Cuando issue #5 (dataset retrospectivo) cierre y haya ≥50 casos reales con ground truth doble ciego:

1. Re-correr la suite con threshold 0.6.
2. Inspeccionar manualmente los matches `fuzzy` y los `mismatch` cercanos al threshold.
3. Si el líder clínico identifica >5% de falsos positivos o falsos negativos en esa banda → escribir ADR superseder que ajuste threshold o cambie estrategia.

**Excepciones por tipo de campo.**

| Campo | Tratamiento |
|---|---|
| `notes_summary` (texto libre largo) | Mismo threshold 0.6 (stub). Migración a embeddings tiene **prioridad alta** aquí porque texto libre es donde difflib falla más. |
| Nombres de labs (`Hemoglobina` vs `HEMOGLOBINA`) | Normalizado lowercase → `exact`. |
| Valores de labs (`"10.8"` vs `"10.80"`) | Exact string match. Sin parsing numérico (preserva formato del documento). TODO R1: parse numeric con tolerancia. |
| Fechas (`fum`, `fpp`, `lab.date`) | Exact match ISO. Sin tolerancia. |
| Edad gestacional (`gestational_age_weeks`) | Tolerancia numérica ±0.5 semanas (no string fuzzy). |
| Edad paciente (`patient_age`) | Exact match int. |

### Decisión 2 — Criticidad del campo se define por proceso, no por intuición

**Regla:** un campo está en `CRITICAL_FIELDS` (peso 2.0) **si y sólo si** se cumple al menos una de estas condiciones:

1. **Decisión clínica directa depende del valor.** Error en el campo → conducta del médico cambia.
2. **Bloque de datos derivados depende del valor.** Error → todos los cálculos derivados están mal (ejemplo paradigmático: `fum` ancla FPP, EG, ventanas de tamizaje).
3. **Omitir el campo equivale a omitir seguimiento clínico activo.** Ejemplo: un `active_problem` no extraído implica que el médico no sabe que existe — el problema deja de seguirse.
4. **Lab con `abnormal = True` en el documento.** No omitir un lab anormal es seguridad clínica básica.

**Conjunto inicial** (definido en `field_comparator.CRITICAL_FIELDS` y documentado en `docs/evaluation/metrics-specification.md` § 1):

`patient_age, gestational_age_weeks, fum, fpp, active_problems, risk_factors`, más cualquier `lab_results[i]` con `abnormal=True`.

**Proceso de cambio.**

- **Agregar un campo crítico:** PR con justificación clínica explícita (cuál de las 4 condiciones cumple) + opinión del líder clínico fundador registrada en el PR. No requiere ADR independiente si la justificación es directa.
- **Quitar un campo crítico:** **Requiere ADR independiente** que supersede parte de este. Quitar criticidad relaja la métrica; nunca se debe hacer para "facilitar" que un modelo pase el gate.
- **Cambiar peso a otro valor distinto de 2.0:** Requiere ADR.

**Validación pendiente.** El conjunto inicial fue compilado por el founder con justificación clínica derivada de STRATEGY § 5.1 (carga clínica) y § 5.2 (problema reformulado). **No fue revisado por un obstetra de carrera todavía.** Antes de R1, el líder clínico fundador (cuando exista) revisa la lista y firma. La revisión queda registrada en el Migration log de este ADR.

### Decisión 3 — Ground truth dudoso se etiqueta, no se incluye en métricas estándar

**Regla:** durante el proceso de doble ciego (ver `evals/GROUND_TRUTH_PROCESS.md`), si el árbitro no puede resolver A vs B con confianza razonable, el caso recibe etiqueta `ground_truth_certainty ∈ {high, moderate, low}` en `expected.meta.json`:

- `high` (default): A y B coinciden en ≥95% campos críticos. Caso usable en métricas estándar.
- `moderate`: A y B difieren en ≤2 campos críticos, árbitro decidió pero con duda explícita registrada. Caso usable en métricas estándar pero **marcado** en reportes.
- `low`: A y B difieren en ≥3 campos críticos, árbitro no pudo decidir con confianza. Caso **se excluye** de métricas estándar.

**Procesamiento de cada nivel.**

| Certainty | En `factual_accuracy_mean` agregado | En `critical_omissions_total` | En `hallucinations_total` | En reportes |
|---|---|---|---|---|
| `high` | ✅ Incluido | ✅ Incluido | ✅ Incluido | Sin nota |
| `moderate` | ✅ Incluido | ✅ Incluido | ✅ Incluido | Anotado: `⚠️ moderate certainty` |
| `low` | ❌ Excluido | ❌ Excluido | ❌ Excluido | Listado en sección separada "casos de baja certeza" |

**Métricas auxiliares para casos `low`.** Se calculan separadamente:

- `low_certainty_count`: cuántos casos del run están en este bucket.
- `low_certainty_rate = low_certainty_count / cases_total`. Si rate > 10% sostenido en runs sucesivos, el proceso de ground truth (no el extractor) tiene problema — revisar.

**Por qué no se incluyen.** Forzar el extractor a matchear ground truth de baja certeza castiga performance sobre algo que ni los humanos saben con certeza. Reportar el dato separado mantiene transparencia.

**Por qué no se descartan completamente.** Casos de baja certeza son **señal clínica real** — son los casos donde el documento es ambiguo. Se preservan para análisis futuro (entrenamiento, calibración, mejora del proceso).

**Implementación pendiente.**

- `evals/GROUND_TRUTH_PROCESS.md` § "Producción independiente" agrega campo `ground_truth_certainty` al schema de `expected.meta.json` cuando inicie producción de ground truth real (issue #5).
- `harness.py::run_all()` lee `certainty` de meta y bucket-iza acordemente.
- TODO R0 cierre: agregar al schema de `TestCase.meta` validación de este campo cuando aparezca.

## Consequences

### Positive

- **Trazabilidad metodológica.** Tres decisiones que afectan toda la suite de evaluación quedan documentadas con justificación. Cuando el modelo falla un gate, podemos preguntar "¿es por la métrica o por el modelo?" con base.
- **Cambios futuros documentados.** Cualquier cambio en threshold, criticidad o tratamiento de ground truth genera ADR — no decisión silenciosa en un commit.
- **Pre-aprobación de revisión clínica.** El proceso para validar criticidad y revalidar threshold está definido antes de que el dataset real llegue. Cuando llegue, sabemos qué hacer.
- **Métricas resistentes a "ajuste por conveniencia".** Decisión explícita: prohibido relajar umbrales sin firma clínica. Anti-patrón de STRATEGY § 10.7 explicitado.

### Negative

- **Threshold 0.6 es provisional.** Está documentado como tal, pero si el dataset real muestra que es muy laxo, hay que revisar. Riesgo: si esa revisión no ocurre antes de R1, R1 podría usar un threshold subóptimo.
- **`CRITICAL_FIELDS` sin firma clínica todavía.** El conjunto inicial es justificable pero no validado por obstetra de carrera. Si un campo crítico está mal puesto (ej. `risk_factors` quizás debería estar separado por tipo de riesgo), el peso 2.0 no captura la importancia real.
- **`ground_truth_certainty` añade complejidad al schema y al harness.** Hay que implementarlo cuando el dataset real llegue; mientras tanto, los casos sintéticos no usan esta categoría (todos son `high` por default).
- **Migración a embeddings semánticos es trabajo significativo.** Hasta que ocurra, hay un techo a la calidad del fuzzy matching.

## Alternatives considered

### Alternativa A: No formalizar — dejar threshold y criticidad en código sin ADR

**Por qué no:**
- El issue #11 lo pide explícitamente: "ADR sobre decisiones difíciles: ¿cómo se trata una paráfrasis verbatim-casi? ¿qué cuenta como 'crítico'? ¿qué pasa cuando ground truth tiene dudas?"
- Sin ADR, el threshold se cambia en un PR menor, los baselines históricos se invalidan silenciosamente.
- Sin proceso documentado para agregar/quitar criticidad, el conjunto se vuelve arbitrario con el tiempo.

### Alternativa B: Threshold de fuzzy más estricto (0.85)

**Por qué no:**
- Probado contra `synthetic_case_01`: 0.85 produce falsos negativos en pares clínicamente equivalentes (`"Anemia leve"` vs `"Anemia leve gestacional"`).
- El extractor naturalmente agrega calificadores ("anemia leve" → "anemia leve gestacional"). Castigar esto como mismatch infla artificialmente las métricas de error.
- 0.6 es laxo pero capturó los pares correctos del fixture; es punto de partida defensible con migración a embeddings como plan B.

### Alternativa C: Threshold per-campo (diferentes thresholds para `active_problems` vs `notes_summary`)

**Por qué no por ahora:**
- Sobreingenierizado para Fase 1. Aumenta superficie de calibración y posibilidad de bug.
- El plan es migrar a embeddings semánticos antes de R2, lo que vuelve el threshold per-campo irrelevante (semantic similarity ya captura naturalmente la diferencia entre dominios).
- Si el dataset real muestra que un campo específico necesita threshold distinto, ADR superseder puede agregarlo.

### Alternativa D: Excluir todos los casos con `ground_truth_certainty < high`

**Por qué no:**
- Pierde señal clínica real. Los casos de baja certeza son **exactamente** donde el copiloto puede aportar valor (resumen para un humano que tampoco está seguro).
- Reduce el dataset efectivo, lo que aumenta varianza de las métricas agregadas.
- Solución intermedia (incluir `moderate`, excluir solo `low`) preserva señal sin contaminar métricas.

### Alternativa E: Ground truth probabilístico (cada campo con confidence interval)

**Por qué no por ahora:**
- Estructura de fixture (`expected.json`) explota en complejidad. Cada campo dejaría de ser un valor para ser una distribución.
- Cambios en comparators, métricas, reporters — todo el harness toca.
- Si la necesidad aparece en producción (volumen real + casos sistemáticamente ambiguos), evaluar en R3+. Hasta entonces, `certainty ∈ {high, moderate, low}` es aproximación pragmática.

## References

- `docs/evaluation/metrics-specification.md` — definición formal de las 4 métricas que dependen de este ADR.
- [ADR 0004](0004-model-routing-policy.md) — Nivel 2 referencia este ADR para sus umbrales operativos.
- `evals/src/sica_evals/comparators/field_comparator.py` — `CRITICAL_FIELDS` y `FUZZY_RATIO_THRESHOLD`.
- `evals/GROUND_TRUTH_PROCESS.md` — proceso de doble ciego que produce `ground_truth_certainty`.
- STRATEGY.md § 10 (los 7 pilares).
- STRATEGY.md § 10.7 — operación continua de evals; anti-patrón de "ajustar métrica para que pase".
- Issue [#11](https://github.com/aaronhuaynate66/sica-platform/issues/11) — Origen de este ADR.

## Migration log

| Fecha | Cambio | Autor | ADR superseder |
|---|---|---|---|
| 2026-05-22 | Creación inicial. Threshold 0.6 provisional. `CRITICAL_FIELDS` con justificación clínica pero sin firma de obstetra todavía. | Aaron Huaynate | — |

**TODOs registrados para futuras entradas del log:**

- [ ] Revisión y firma del conjunto `CRITICAL_FIELDS` por líder clínico fundador antes de R1.
- [ ] Revalidación de threshold 0.6 con ≥50 casos reales del partner cuando issue #5 cierre.
- [ ] Migración de fuzzy stub a embeddings semánticos (`sentence-transformers` o equivalente) en R2.
- [ ] Implementación del campo `ground_truth_certainty` en schema cuando ground truth real entre al harness.
