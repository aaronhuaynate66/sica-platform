# evals/ — SICA Evaluation Harness

Suite de evaluación clínica de SICA. Implementa los **siete pilares** descritos en `STRATEGY.md` § 10 y los criterios condicionales de `docs/decisions/0004-model-routing-policy.md` § Nivel 2.

## Qué es

`sica-evals` es un paquete Python instalable (`pip install -e .`) que mide la calidad del `clinical-extractor` de forma **reproducible**, **determinística** (a nivel del harness, no del modelo) y **auditable**. Es el motor que decide si el gate de salida R0 (≥85% factual accuracy, ≤5% omisiones críticas) se cumple.

## Estado

R0 — esqueleto operativo. La suite real arranca con el primer dataset retrospectivo del partner fundador (issue #5). Hoy corre contra fixtures sintéticas commiteables.

## Arquitectura

```
evals/
├── README.md                          ← este archivo
├── pyproject.toml                     ← paquete sica-evals
├── src/sica_evals/
│   ├── schemas.py                     ← TestCase, FieldComparison, CaseResult, HarnessReport
│   ├── harness.py                     ← orquestador principal + diff_reports
│   ├── cli.py                         ← sica-eval {run, report, diff}
│   ├── metrics/                       ← factual_accuracy, critical_omissions, hallucinations, calibration
│   ├── comparators/                   ← field_comparator, span_comparator
│   ├── reporters/                     ← json, markdown, html (standalone)
│   └── extractors/                    ← MockExtractor, ClinicalExtractorWrapper
├── tests/                             ← 31 tests, todos contra MockExtractor
├── fixtures/                          ← casos sintéticos commiteables (NUNCA PHI real)
└── reports/                           ← outputs del harness (gitignored, solo .gitkeep)
```

> **Nota sobre estructura.** El issue #10 proponía carpetas separadas `datasets/`, `ground_truth/`, `harness/`, `metrics/`. Adoptamos en su lugar el layout estándar de paquete Python con módulos bajo `src/sica_evals/`. Los conceptos del issue se mapean así: `harness/` → `harness.py`, `metrics/` → `metrics/*.py`. Los `datasets/` y `ground_truth/` con PHI real **no viven en el repo** (ver `.gitignore` + `GROUND_TRUTH_PROCESS.md`).

## Instalación

```bash
cd evals
pip install -e ".[dev]"
```

Para integración con el `clinical-extractor` real (requiere `ANTHROPIC_API_KEY`):

```bash
cd evals
pip install -e ".[dev,extractor]"
```

## Uso

### Correr la suite

```bash
# Default: MockExtractor (devuelve el fixture esperado, valida la pipeline)
sica-eval run --format all

# Solo un caso
sica-eval run --filter synthetic_case_01 --format markdown

# Con el extractor real (consume API y dinero)
sica-eval run --extractor clinical --format json
```

Salida: `evals/reports/{timestamp}_{run_id}.{json,md,html}`.

### Ver un reporte

```bash
sica-eval report evals/reports/20260522T004610Z_9a71c08b.json
```

Imprime el Markdown a stdout.

### Comparar corridas (diff)

```bash
sica-eval diff reports/run_a.json reports/run_b.json
```

Útil como gate de PR: si tocaste un prompt o cambiaste de modelo, esta comparación te dice si subiste o bajaste cada métrica.

## Métricas

**Especificación formal:** [`docs/evaluation/metrics-specification.md`](../docs/evaluation/metrics-specification.md). Cualquier cambio a las métricas pasa primero por la spec, después por el código. **Decisiones metodológicas** (threshold de fuzzy, criticidad, ground truth dudoso) en [ADR 0005](../docs/decisions/0005-evaluation-methodology.md).

### Implementadas en R0

| Métrica | Módulo | Spec § | Umbral R0 |
|---|---|:---:|---:|
| Factual accuracy (ponderada) | `metrics.factual_accuracy` | 1 | `≥ 0.85` |
| Critical omissions | `metrics.critical_omissions` | 2 | `≤ 5 / run` |
| Hallucinations (H_field + H_span) | `metrics.hallucinations` | 3 | `= 0` |
| Confidence calibration error (ECE) | `metrics.calibration` | 4 | `≤ 0.15` |

Mini-doc operativo de los módulos en [`src/sica_evals/metrics/README.md`](src/sica_evals/metrics/README.md).

### Correr solo los tests de métricas

```bash
# Implementación
python -m pytest tests/test_metrics.py -v

# Spec compliance (verifica que el código cumple metrics-specification.md)
python -m pytest tests/test_metrics_spec.py -v
```

### Pendientes (pilares 4-7 de STRATEGY § 10)

Spec preliminar en [`metrics-specification.md`](../docs/evaluation/metrics-specification.md) § 5-8:

- **Physician disagreement scoring** (pilar 4) — necesita uso clínico real. R2+.
- **Longitudinal consistency** (pilar 5) — necesita múltiples encuentros por paciente. R3.
- **Temporal reasoning** (pilar 6) — necesita suite sintética por médico. R1+.
- **Synthetic patient testing en volumen** (pilar 7) — STRATEGY § 10.4. R1+.

## Cómo agregar un nuevo test case

1. **PDF sintético**: colocar en `services/clinical-extractor/data/` (commiteable solo si **claramente marcado** como sintético — ver `.gitignore`) o en object storage privado si es PHI real desidentificada.
2. **Expected output** (`{case_id}.expected.json`): un ObstetricSummary serializado. Para sintéticos puede generarse con el extractor + revisión humana. Para reales, debe venir de **doble revisión médica** (ver `GROUND_TRUTH_PROCESS.md`).
3. **Metadata** (`{case_id}.expected.meta.json`): tipo de baseline, revisor humano, hash del PDF, fecha. Ver `fixtures/README.md` para esquema.
4. Correr `sica-eval run --filter {case_id}` para validar.

## Cómo extender las métricas

Cada métrica vive en su propio módulo bajo `metrics/`. Para agregar una:

1. Crear `metrics/mi_metrica.py` con función pura sobre `list[FieldComparison]` o `list[CaseResult]`.
2. Exportarla en `metrics/__init__.py`.
3. Llamarla en `harness.py::run_case` o `harness.py::run_all` y agregar el resultado a `CaseResult` o `HarnessReport.aggregate_metrics`.
4. Tests en `tests/test_metrics.py`.
5. Si la métrica afecta el gate de salida, actualizar `reporters/markdown_reporter.py::_passes_gate` y `reporters/html_reporter.py::gate_pass`.

## Determinismo y reproducibilidad

- **El harness es determinístico.** Sin `now()`, sin `random()` propio.
- **El extractor puede ser no-determinístico.** Los LLM sin seed dan outputs distintos en cada corrida. Por eso cada reporte registra `extractor_version`, `model_used`, `git_commit`, `host`, `timestamp`.
- **Cada PR que toque prompts o modelos** debería correr la suite (gate manual). El gate automático en CI queda como TODO (issue separado): un workflow que falle el merge si `factual_accuracy` cae más de 3 puntos respecto a la corrida en `main`.

## Sin PHI en el repo

El `.gitignore` bloquea PDFs por default (`*.pdf`). Solo se permiten excepciones explícitas, todas sintéticas, listadas allí. **Nunca commitear**: historias clínicas reales, ground truth con PHI, datasets de partners. Estos van en object storage privado cifrado (ver `docs/security/data-handling.md` § 3-4).

## Referencias

- `STRATEGY.md` § 10 — AI Evaluation Infrastructure (7 pilares).
- `STRATEGY.md` § 7 — Gate R0 (≥85% factualidad, ≤5% omisiones).
- `STRATEGY.md` § 12.3 — Métricas de validación clínica.
- [ADR 0004](../docs/decisions/0004-model-routing-policy.md) — Política de routing de modelos + umbrales (Nivel 2).
- [ADR 0003](../docs/decisions/0003-security-and-phi-policy.md) — Política de PHI.
- `services/clinical-extractor/` — Servicio bajo evaluación.
- `evals/GROUND_TRUTH_PROCESS.md` — Proceso de doble revisión médica.
- `evals/fixtures/README.md` — Convenciones de fixtures.
- Issue [#10](https://github.com/aaronhuaynate66/sica-platform/issues/10) — Origen de este harness.

## Principios

- **Test set congelado.** Cambios al test set requieren ADR explícito.
- **Regression antes de merge.** Cualquier cambio de prompt o modelo corre la suite completa (gate manual hoy, CI gate TODO).
- **Sin PHI en el repo.** Solo `fixtures/` (sintético, marcado) entra al git.
- **Schema-stable reports.** El JSON output cumple `HarnessReport` siempre — base para diffing entre corridas.
