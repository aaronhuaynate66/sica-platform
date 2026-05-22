# sica_evals.metrics

Implementación de referencia de las métricas de factualidad clínica de SICA.

**La especificación formal vive en [`docs/evaluation/metrics-specification.md`](../../../../docs/evaluation/metrics-specification.md).** Este README es un índice operativo para quien necesite extender el código.

## Mapeo módulo → spec

| Módulo | Métrica | Sección de la spec | Umbral R0 |
|---|---|---|---:|
| `factual_accuracy.py` | Factual Accuracy ponderada | § 1 | `≥ 0.85` |
| `critical_omissions.py` | Critical Omissions | § 2 | `≤ 5 / run` |
| `hallucinations.py` | Hallucinations (H_field + H_span) | § 3 | `= 0` |
| `calibration.py` | Expected Calibration Error (ECE) | § 4 | `≤ 0.15` |

## API pública

Cada módulo expone la API canónica que el harness usa (signatura sobre `list[FieldComparison]`) y wrappers de conveniencia que aceptan `(expected, actual)` directamente (signatura del issue #11).

| Función canónica | Wrapper de conveniencia |
|---|---|
| `compute_factual_accuracy(comparisons)` | `compute_factual_accuracy_from_summary(expected, actual)` |
| `count_critical_omissions(comparisons)` | `count_critical_omissions_against(expected, actual, critical_fields=None)` |
| `detect_hallucinations(comparisons)` | _(usar via comparisons; los inputs ya son explícitos)_ |
| `compute_calibration_error(case_results, n_bins=10)` | _(opera a nivel run, no caso individual)_ |

Adicionales útiles:

- `compute_factual_accuracy_critical_only(comparisons)` — para tracker del umbral R3+ (≥0.95 sobre críticos solamente).
- `count_hallucinations_by_kind(comparisons)` — separa `(|H_field|, |H_span|)` para triage.
- `list_critical_omissions(comparisons)` — devuelve los `FieldComparison` flageados, útil para reporters.
- `compute_case_calibration_error(reported_conf, observed_acc)` — error per-case directo.

## Cómo agregar una métrica nueva

1. **Definir formalmente** en `docs/evaluation/metrics-specification.md` antes de escribir código (sección numerada nueva o subsección).
2. **Crear archivo** `mi_metrica.py` con función pura y docstring que referencia la spec.
3. **Exportar** en `__init__.py`.
4. **Integrar en harness** (`harness.py::run_case` o `run_all`) si aplica al gate o al aggregate.
5. **Tests:**
   - `tests/test_metrics.py` — casos básicos de implementación.
   - `tests/test_metrics_spec.py` — casos canónicos que verifican que el código cumple la spec literalmente.
6. **Si la métrica afecta el gate de salida,** actualizar `reporters/markdown_reporter.py::_passes_gate` y `reporters/html_reporter.py::gate_pass`.

## Cómo correr solo los tests de métricas

```bash
cd evals
python -m pytest tests/test_metrics.py tests/test_metrics_spec.py -v
```

Para correr únicamente los tests spec-driven (validación de que código cumple `metrics-specification.md`):

```bash
python -m pytest tests/test_metrics_spec.py -v
```

## Estado pendiente

- **Validación clínica de pesos** (`CRITICAL_FIELDS` en `comparators/field_comparator.py`) — requiere firma de líder clínico. Ver [ADR 0005](../../../../docs/decisions/0005-evaluation-methodology.md) Migration log.
- **Migración a embeddings semánticos** para reemplazar `difflib.SequenceMatcher` en `notes_summary` y string lists. Stub provisional con threshold 0.6.
- **Validación de `compute_calibration_error` con N grande.** La reconstrucción de confidence desde `confidence_calibration_error` tiene sesgo pequeño cuando hay mezcla de over- y under-confidence en un mismo bin; aceptable para N de R0 pero validar en R1.
- **Implementación de los pilares 4–7** de STRATEGY § 10 (physician disagreement scoring, longitudinal consistency, temporal reasoning, synthetic patient testing en volumen). Spec preliminar en `metrics-specification.md` § 5–8.
