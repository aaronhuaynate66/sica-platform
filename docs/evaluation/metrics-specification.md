# Métricas de factualidad clínica — Especificación formal

**Versión:** 0.1
**Última actualización:** 2026-05-22
**Audiencia:** ingenieros que extienden el harness, líder clínico que valida pesos, auditor regulatorio, asesor metodológico.
**Estado:** Norma vigente. Cambios requieren ADR nuevo que supersede partes de este documento. Ver § Política de cambio.

---

## Contexto

SICA mide la calidad del `clinical-extractor` con métricas **clínicamente significativas**, no métricas genéricas de NLP (BLEU/ROUGE/METEOR/etc.). Razones:

1. **BLEU/ROUGE miden overlap n-gram contra una referencia.** En extracción clínica, el output es **estructurado** (campos del schema `ObstetricSummary`), no texto libre. Un BLEU alto no implica que la edad gestacional sea correcta.
2. **El gate de R0 → R1 es clínico.** STRATEGY § 7 lo declara: "MedGemma 4B ≥85% factualidad, ≤5% omisiones críticas". Ese 85% se refiere a hechos clínicos, no a n-grams compartidos.
3. **El sesgo de las métricas genéricas** favorece outputs verbosos que copian fragmentos del input. Eso es exactamente lo que no queremos — queremos extracción estructurada con evidencia trazable.

Este documento define **formalmente** las 4 métricas implementadas en `evals/src/sica_evals/metrics/` y las 4 pendientes de STRATEGY § 10. Cada definición tiene: fórmula, denominador, casos límite, umbral por release, justificación clínica.

Referencias canónicas:

- STRATEGY § 10 (los 7 pilares).
- ADR 0004 § Nivel 2 (umbrales por modelo y tarea).
- [ADR 0005](../decisions/0005-evaluation-methodology.md) — Decisiones metodológicas que sustentan estas definiciones.
- `evals/src/sica_evals/metrics/` — implementación de referencia.
- `evals/tests/test_metrics_spec.py` — tests que verifican que el código cumple esta spec.

---

## Métricas core (implementadas en R0)

### 1. Factual Accuracy (ponderada)

**Definición formal.**

Sea `C` el conjunto de `field_comparisons` producido por `compare_obstetric_summary(expected, actual)` (ver `comparators/field_comparator.py`). Cada `c ∈ C` tiene:

- `w(c) ∈ ℝ⁺` — peso del campo. `w = 2.0` si el campo es crítico, `1.0` en otro caso.
- `match(c) ∈ {0, 1}` — verdicto binario del comparator.

```
                Σ_{c ∈ C}  w(c) · match(c)
factual_accuracy = ─────────────────────────
                     Σ_{c ∈ C}  w(c)
```

Si `Σ w(c) = 0` (sin campos comparables), el resultado es `0.0` por convención.

**Match types** que producen `match(c) = 1`:

| Tipo | Condición | Ejemplo |
|---|---|---|
| `exact` | Igualdad estricta tras normalización (lowercase + strip whitespace) | `"FUM"` vs `"fum"` → exact |
| `fuzzy` | Similitud `≥ FUZZY_RATIO_THRESHOLD` o numérico dentro de tolerancia | `"Anemia leve"` vs `"Anemia leve gestacional"` con ratio 0.73 → fuzzy si threshold=0.6 |
| `semantic` | Similitud de embeddings `≥ SEMANTIC_THRESHOLD` (**TODO**, ver [ADR 0005](../decisions/0005-evaluation-methodology.md)) | _(pendiente)_ |

**Match types** que producen `match(c) = 0`:

| Tipo | Condición |
|---|---|
| `missing` | Esperado no nulo, actual nulo/ausente. |
| `hallucinated` | Esperado nulo/ausente, actual no nulo. |
| `mismatch` | Ambos no nulos pero no coinciden ni por fuzzy ni por tolerancia. |

**Tolerancias numéricas y de fecha.** Constantes en `comparators/field_comparator.py`:

| Campo | Tolerancia | Justificación |
|---|---|---|
| `gestational_age_weeks` | `± 0.5 semanas` | Ambigüedad razonable entre FUM y ecografía; 0.5 semanas no cambia decisión clínica. |
| `fum`, `fpp` | Exact match (sin tolerancia) | Una FUM con diferencia de un día cambia el percentil de crecimiento. |
| `patient_age` | Exact match | Categórico operacionalmente. |
| Lab `value` | Exact match de string (no parsing numérico todavía) | El extractor preserva formato literal del documento. Parsing numérico es futuro (TODO R1). |

**Umbral fuzzy.** `FUZZY_RATIO_THRESHOLD = 0.6` provisional sobre `difflib.SequenceMatcher.ratio()`. Calibrado contra el caso sintético `synthetic_case_01`. **TODO clínico:** validar el umbral contra dataset retrospectivo real cuando issue #5 cierre. Decisión metodológica completa en [ADR 0005](../decisions/0005-evaluation-methodology.md) § "Paráfrasis verbatim-casi".

**Campos críticos** (`w = 2.0`). Definidos en `comparators/field_comparator.CRITICAL_FIELDS`:

| Campo | Justificación clínica |
|---|---|
| `patient_age` | Decisión obstétrica varía radicalmente entre <18, 18–34, ≥35 años (edad materna avanzada cambia plan completo). |
| `gestational_age_weeks` | Define ventana de tamizajes, viabilidad fetal, decisiones sobre maduración pulmonar, conducta de parto. Error sistemático → daño clínico real. |
| `fum` | Anchor temporal de todo el embarazo. FUM mal → todo lo derivado (FPP, EG por FUM, ventanas de cribado) está mal. |
| `fpp` | Define ventana de parto programado (cesárea iterativa típicamente entre 38–39 sem). Error de 1 semana cambia conducta. |
| `active_problems` | Lista de seguimiento clínico. Omitir un problema activo → omisión de control. |
| `risk_factors` | Cambian plan de control prenatal completo (frecuencia de controles, derivación). |
| Labs con `abnormal=True` | Anormalidad en hemoglobina, glucosa, urocultivo, RPR/HIV, etc. cambia conducta inmediata. Omitir un lab anormal es omisión clínica grave. |

Pesos asignados automáticamente por `field_comparator._weight_for()`. Cualquier extensión a `CRITICAL_FIELDS` requiere PR con justificación clínica explícita.

**Umbrales por release.**

| Release | Umbral mínimo | Sobre qué dataset | Justificación |
|---|---:|---|---|
| **R0** | `≥ 0.85` | 150-200 historias retrospectivas del partner (cuando issue #5 cierre) | Gate explícito de STRATEGY § 7. Coherente con [ADR 0004 Nivel 2](../decisions/0004-model-routing-policy.md). |
| **R1** | `≥ 0.90` | Mismo dataset + casos shadow R2 | Madurez del extractor y prompts en R1. |
| **R3+** | `≥ 0.95` sobre **campos críticos solamente** | Producción asistiva | STRATEGY § 12.3 — clínicamente seguro para handoff. |

**Ejemplo numérico.**

```
Comparaciones (4 campos):
  patient_age:            w=2.0, match=1   → 2.0
  gestational_age_weeks:  w=2.0, match=1   → 2.0
  fum:                    w=2.0, match=0   → 0.0   ← crítico fallido
  notes_summary:          w=1.0, match=1   → 1.0

Σ w·match = 2 + 2 + 0 + 1 = 5
Σ w       = 2 + 2 + 2 + 1 = 7
factual_accuracy = 5 / 7 ≈ 0.7143
```

Caso límite: si todos los campos críticos fallan pero los no críticos pasan, `factual_accuracy ≤ 0.43` (peso de no críticos divididos por peso total). Es deliberadamente bajo.

**Casos límite del cómputo.**

- `comparisons = []` → `0.0` (no se puede medir lo que no se comparó).
- Todos los matches = 1 → `1.0`.
- Todos los matches = 0 → `0.0`.
- Comparaciones con `weight = 0.0` → ignoradas en numerador y denominador.

**Variante: `compute_factual_accuracy_critical_only`** (`metrics/factual_accuracy.py`).

```
                          |{ c ∈ C_critical : match(c) = 1 }|
critical_only_accuracy = ─────────────────────────────────────
                                       |C_critical|
```

donde `C_critical = { c ∈ C : w(c) ≥ 2.0 }`. Si `C_critical = ∅`, devuelve `0.0`. Útil para verificar el umbral R3+ "≥0.95 sobre críticos".

---

### 2. Critical Omissions

**Definición formal.**

Sea `O = { c ∈ C : w(c) ≥ 2.0 ∧ match_type(c) = missing }`.

```
critical_omissions = |O|
```

Es un **conteo absoluto**, no una tasa, por construcción. La tasa relativa al total de comparaciones críticas se puede computar derivadamente, pero la métrica primaria del gate es el conteo.

**Cómo se detecta `missing` en cada tipo de campo.**

| Tipo de campo | Condición `missing` |
|---|---|
| Escalar opcional (`patient_age`, `fum`, `fpp`) | `expected ≠ None ∧ actual = None` |
| Lista de strings (`active_problems`, `risk_factors`) | Element específico en `expected` sin match fuzzy en `actual` |
| `lab_results[i]` con `expected[i].abnormal = True` | Ausencia del lab por nombre en `actual.lab_results` |
| `notes_summary` | `expected ≠ ""` y `actual = ""` |

**Casos especiales.**

- **Listas vacías en actual cuando expected tiene elementos.** Esto se descompone en múltiples comparaciones (una por elemento esperado). Cada elemento sin match cuenta 1 omisión.
- **Sub-campos de lab_results.** El comparator emite un `FieldComparison` por atributo del lab (`name`, `value`, `unit`, `date`, `abnormal`). Si un lab anormal está totalmente ausente, emite **un único `FieldComparison` agregado** con `field_name = lab_results[i:name]` y `weight = 2.0`. Cuenta como **1 omisión** (no 5).
- **Lab anormal presente pero con `abnormal` cambiado a `False`.** No es omisión: es `mismatch` (campo presente pero divergente). Reduce factual_accuracy pero no aumenta critical_omissions. Decisión metodológica: ver [ADR 0005](../decisions/0005-evaluation-methodology.md) § "Mismatch vs omisión".

**Umbrales por release.**

| Release | Umbral máximo | Por caso o por run |
|---|---:|---|
| **R0** | `≤ 5` | Por run completo (suma sobre todos los casos) |
| **R1** | `≤ 2` | Por run completo |
| **R2 shadow** | `≤ 1` | Sobre casos categorizados como "críticos" (ej. preeclampsia, gemelar, RPM) |

**Justificación.** El gate "≤5 omisiones críticas" significa: en un dataset de 50-200 casos, el extractor puede omitir hasta 5 hechos críticos en total. Un médico puede absorber esa carga revisando outputs. >5 omisiones = el copiloto deja de ahorrar tiempo neto.

**Ejemplo numérico.** Sobre un run de 50 casos:

```
case_001:  0 omisiones críticas
case_002:  1 omisión (fum faltante)
case_003:  2 omisiones (active_problems vacío, hemoglobina anormal ausente)
...
case_050:  0 omisiones

Σ = 4
critical_omissions_total = 4   → PASS (≤5)
```

---

### 3. Hallucinations

**Definición formal.**

Sea:

- `H_field = { c ∈ C : match_type(c) = hallucinated ∧ ¬c.field_name comienza con "evidence_spans" }`
- `H_span = { c ∈ C : match_type(c) = hallucinated ∧ c.field_name comienza con "evidence_spans" }`

```
hallucinations = |H_field| + |H_span|
```

**Detección de `H_field`** (en `comparators/field_comparator.py`):

- Para escalares: `expected = None ∧ actual ≠ None`.
- Para listas: elemento en `actual` sin match fuzzy en `expected`.
- Para labs: lab presente en `actual` cuyo `name` no aparece en `expected.lab_results`.

**Detección de `H_span`** (en `comparators/span_comparator.py`):

- Para cada `EvidenceSpan e ∈ actual.evidence_spans`: verificar si `e.source_text` existe (literal o normalizado por whitespace) en el texto del PDF fuente.
- Si **no** existe en el PDF → hallucination de evidencia (span fabricado).
- Si existe en el PDF pero no matchea ningún span esperado → no necesariamente hallucination, puede ser evidencia adicional válida (clasificado `fuzzy` con score 0.5, no cuenta como hallucination).

**Por qué la asimetría.** Una evidencia extra que sí está en el PDF no es alucinación — es información adicional que el médico puede o no querer. Una evidencia que no está en el PDF es invento puro, fallo grave.

**Conservadurismo cuando no hay PDF text.** Si el harness no recibe el texto del PDF (parámetro `pdf_text=None` en `compare_evidence_spans`), `span_in_text()` retorna `True` por defecto. El span se asume soportado. Esto evita falsos positivos cuando el harness opera sobre fixtures sin acceso al PDF. **Trade-off documentado:** algunas hallucinations de span pueden pasar desapercibidas. Mitigación: el harness debería siempre proveer `pdf_text` cuando está disponible. TODO R1: extraer PDF text dentro del harness automáticamente.

**Umbral por release.**

| Release | Umbral | Justificación |
|---|---:|---|
| **R0** | `= 0` | Sin tolerancia. Una sola hallucination clínica creíble mata adopción y confianza médica. |
| **R1+** | `= 0` | Idem. No hay relajación esperada. |

**Por qué cero.** STRATEGY § 11.1 principio 4: "abstención sobre alucinación". El sistema debe decir "no encontrado" antes que inventar. Cualquier hallucination en producción es violación de principio arquitectónico, no parámetro ajustable.

**Ejemplo numérico.**

```
case_001:
  - active_problems incluye "Diabetes tipo 2" que NO está en el documento.
    → H_field += 1
  - evidence_spans incluye claim "TSH 4.5 mUI/L" con source_text "TSH: 4.5"
    pero el PDF dice "TSH: 2.1 mUI/L".
    → H_span += 1
  - hallucinations = 2 → FAIL del gate.
```

**Salida.** `detect_hallucinations(comparisons)` devuelve `list[str]` con descripción legible de cada hallucination encontrada (campo afectado, valor problemático). Usado por reporters para Hallazgos críticos.

---

### 4. Confidence Calibration Error (ECE)

**Definición formal.** Expected Calibration Error con `K` bins.

Sea `R` el conjunto de `CaseResult` de un run, particionado en `K` bins por `factual_accuracy`:

```
B_k = { r ∈ R : (k-1)/K ≤ accuracy(r) < k/K }   para k = 1..K
```

Para cada bin no vacío, sea:

- `acc(B_k) = (1/|B_k|) · Σ accuracy(r)`
- `conf(B_k) = (1/|B_k|) · Σ confidence(r)` — el confidence reportado por el extractor

```
ECE = Σ_{k=1..K}  (|B_k| / |R|) · | conf(B_k) - acc(B_k) |
```

**Implementación.** `metrics/calibration.py::compute_calibration_error()`. Por default `K = 10` bins. Parametrizable vía argumento `n_bins`.

**Per-case calibration error.** El harness almacena por caso `r.confidence_calibration_error = |confidence_reportado - factual_accuracy|` para que reporters puedan mostrar la calibración por caso sin recomputar ECE.

**Interpretación.**

| ECE | Lectura |
|---|---|
| `0.00 – 0.05` | Calibración excelente. Confiable para abstención automática. |
| `0.05 – 0.10` | Calibración aceptable. Abstención funciona con margen. |
| `0.10 – 0.15` | Sobreconfianza moderada. Típico de LLMs sin calibración explícita. |
| `> 0.15` | Sobreconfianza severa. La abstención por threshold de confidence **no es confiable**. |
| `> 0.25` | Calibración pobre. El confidence reportado es ruido. Considerar recalibración (Platt, isotonic) o no usar para abstención. |

**Umbrales por release.**

| Release | Umbral máximo |
|---|---:|
| **R0** | `≤ 0.15` |
| **R1+** | `≤ 0.10` |

**Por qué importa.** STRATEGY § 11.4: "Cualquier output con baja confianza → abstención obligatoria". Si el confidence está descalibrado, el sistema de abstención **no protege**. STRATEGY § 10.5 declara calibración como pilar de hallucination detection en producción.

**Ejemplo numérico.** Con 5 casos:

```
case  conf  acc
c1    0.95  0.90   → bin 9 (0.9-1.0)
c2    0.90  0.85   → bin 8 (0.8-0.9)
c3    0.92  0.88   → bin 8
c4    0.80  0.95   → bin 9
c5    0.85  0.80   → bin 7 (0.7-0.8)

bin 7: |B| = 1, acc=0.80, conf=0.85, gap=0.05
bin 8: |B| = 2, acc=0.865, conf=0.91, gap=0.045
bin 9: |B| = 2, acc=0.925, conf=0.875, gap=0.05

ECE = (1/5)·0.05 + (2/5)·0.045 + (2/5)·0.05
    = 0.01 + 0.018 + 0.02 = 0.048   → calibración excelente
```

**Casos límite.**

- `|R| = 0` → ECE = `0.0` por convención (no hay datos).
- Todos los casos en un solo bin → ECE = `|conf - acc|` de ese bin.
- `confidence_calibration_error` ya almacenado en cada `CaseResult` permite reconstruir ECE sin re-correr el harness.

---

## Métricas secundarias (no implementadas en R0)

Las 4 métricas pendientes de STRATEGY § 10. Definición esperada documentada aquí para que cuando se implementen, el código respete la spec.

### 5. Physician Disagreement Scoring (STRATEGY § 10.3)

**Idea.** No mide al modelo contra ground truth, sino el modelo contra **ediciones del médico en producción**. Cada output que el médico edita se categoriza en `acceptance_categories ∈ {factual_fix, critical_addition, style, emphasis, removal}`.

**Definición formal preliminar:**

- `acceptance_rate = |{ outputs accepted sin edit }| / |{ outputs revisados }|`
- `disagreement_index = (1/|outputs|) · Σ severity(category)` donde `severity(factual_fix) = 3, severity(critical_addition) = 3, severity(style) = 1, severity(emphasis) = 1, severity(removal) = 2`.

**Dependencia.** Requiere uso clínico real (R2 shadow mode mínimo, R3 piloto asistivo idealmente). No se puede medir sin médicos editando outputs en producción.

**Release de implementación:** R2.

### 6. Longitudinal Consistency (STRATEGY § 10.5 inciso longitudinal)

**Idea.** Sobre la misma paciente atendida en distintos encuentros, el modelo debe producir outputs coherentes entre sí: la edad gestacional crece linealmente con el tiempo, la FUM no cambia, los problemas activos se acumulan o resuelven con razón documentada.

**Definición formal preliminar:**

- Para cada par `(t1, t2)` con `t1 < t2` sobre la misma paciente:
  - `Δ_egw = actual_egw(t2) - actual_egw(t1)` debe estar entre `(t2 - t1) / 7 · 0.8` y `(t2 - t1) / 7 · 1.2` (semanas calendario ± 20% tolerancia).
  - `actual_fum(t1) = actual_fum(t2)` exacto (no cambia entre encuentros).
- `longitudinal_consistency_rate = |pares consistentes| / |pares totales|`.

**Dependencia.** Requiere múltiples encuentros indexados por paciente. Issue #5 + R3 (handoff materno-neonatal).

**Release de implementación:** R3.

### 7. Temporal Reasoning (STRATEGY § 10 pilar 6)

**Idea.** Probar el extractor sobre casos diseñados para fallar en razonamiento temporal: FUM ambigua, EG por ecografía vs FUM divergente, ventanas críticas (ej. ecografía morfológica a las 20-22 semanas).

**Definición formal preliminar:**

- Suite de N casos sintéticos diseñados por médico con ground truth.
- Métrica: factual_accuracy sobre subset de campos temporales (`egw`, `fum`, `fpp`).
- Threshold: ≥0.90 (más estricto que el agregado porque son casos diseñados).

**Dependencia.** Requiere construcción manual de casos por médico (STRATEGY § 10.4).

**Release de implementación:** R1 (casos sencillos) → R3 (casos complejos).

### 8. Synthetic Patient Testing en volumen (STRATEGY § 10.4)

**Idea.** Catálogo de casos sintéticos cubriendo edge cases clínicos: preeclampsia clásica, atípica, HELLP, eclampsia, postparto; RPM con corioamnionitis; gemelar con discordancia. Cada caso con ground truth firmado por especialista.

**Definición formal.** No es métrica única — es subset del `factual_accuracy` corrido sobre la suite sintética. Métrica derivada: `synthetic_pass_rate = |casos con accuracy ≥ 0.95| / |casos totales|`.

**Dependencia.** Construcción manual por médicos especialistas. STRATEGY § 10.4 lista las primeras 5 variantes de preeclampsia.

**Release de implementación:** R1+ (cinco casos de preeclampsia primero), expansión continua.

---

## Validación de las métricas mismas

¿Cómo sabemos que las métricas miden lo que decimos que miden?

1. **Tests unitarios** en `evals/tests/test_metrics.py` (31 tests) + `test_metrics_spec.py` (8+ tests adicionales spec-driven). Cada caso canónico verifica una propiedad concreta de la spec.
2. **Casos canónicos garantizados**:
   - Caso perfecto → `factual_accuracy = 1.0, omissions = 0, hallucinations = 0, ECE ≤ ε`.
   - Caso vacío → `factual_accuracy = 0.0, omissions = N` (donde N es el conteo de campos críticos esperados no nulos).
   - Caso hallucination pura → `hallucinations ≥ 1`.
   - Caso confidence descalibrado → `ECE > 0.15`.
3. **Roundtrip de Pydantic.** Las estructuras de output (`CaseResult`, `HarnessReport`) se serializan a JSON y se re-cargan sin pérdida. Tests verifican.
4. **TODO clínico:** revisión de los pesos `CRITICAL_FIELDS` y los umbrales de tolerancia por **líder clínico fundador** antes de R1. Sin esta revisión, los pesos son ingeniería educada, no decisión clínica firmada. La revisión queda registrada como entrada en ADR 0005 Migration log.

---

## Política de cambio

Cualquier modificación de:

- Definición matemática de una métrica.
- Lista `CRITICAL_FIELDS` (agregar / quitar campos).
- Tolerancias numéricas o de fecha.
- Umbrales por release (R0, R1, R2, R3+).

requiere:

1. **ADR nuevo** que documente el cambio + justificación + ADR previo que se supersedea (cuando aplica).
2. **Re-ejecutar todos los baselines registrados** con la nueva métrica. Sin esto, los reportes pre-cambio y post-cambio no son comparables.
3. **Actualizar `evals/src/sica_evals/metrics/`** acorde.
4. **Actualizar este documento** (incrementar versión, agregar entrada en historia).
5. **Re-correr tests `test_metrics_spec.py`** y agregar tests para el caso que motivó el cambio.

**Cambios prohibidos sin firma clínica explícita:**

- Bajar un umbral por release sin justificación documentada (sería "ajustar la métrica para que pase el modelo", anti-patrón documentado en STRATEGY § 10.7).
- Quitar un campo de `CRITICAL_FIELDS` sin firma del líder clínico.
- Cambiar la fórmula de `factual_accuracy` para que pondere n-grams o longitud de texto.

---

## Historia

| Versión | Fecha | Cambio | Autor |
|---|---|---|---|
| 0.1 | 2026-05-22 | Spec inicial. Define las 4 métricas core + lista las 4 pendientes. | Founder + Claude Code |

---

## Referencias

- STRATEGY.md § 10 (los 7 pilares de Eval Infrastructure).
- STRATEGY.md § 7 (gate R0).
- STRATEGY.md § 12.3 (validación clínica — métricas objetivo).
- [ADR 0004](../decisions/0004-model-routing-policy.md) § Nivel 2 (umbrales operativos por modelo).
- [ADR 0005](../decisions/0005-evaluation-methodology.md) (decisiones metodológicas: paráfrasis, criticidad, ground truth dudoso).
- `evals/src/sica_evals/metrics/` — implementación.
- `evals/src/sica_evals/comparators/field_comparator.py` — `CRITICAL_FIELDS` y pesos.
- `evals/GROUND_TRUTH_PROCESS.md` — cómo se produce el `expected` que alimenta estas métricas.
- Issue [#11](https://github.com/aaronhuaynate66/sica-platform/issues/11) — Origen de este documento.
