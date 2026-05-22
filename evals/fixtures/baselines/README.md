# evals/fixtures/baselines/ — Snapshots de corridas firmadas

Esta carpeta contiene **snapshots persistidos** de corridas del harness que pasaron todos los gates R0. Son la única clase de reportes del harness que se commitea al repo (el resto vive en `evals/reports/` y está gitignored).

## Propósito

Cada baseline responde **una pregunta concreta**:

> "Con el extractor X versión Y, modelo Z y prompt vN, ¿qué calidad obtenemos sobre el caso C en este momento?"

Son útiles para:

- **Detectar regresiones** cuando se actualiza el extractor, el prompt o el modelo. Comparar nueva corrida vs baseline con `sica-eval diff`.
- **Documentar el techo de calidad** alcanzable sobre PDFs sintéticos claros. Lo que veamos en producción con PDFs reales suele ser inferior a este techo.
- **Reproducibilidad investigativa** cuando hay duda sobre por qué algo cambió. Cada baseline incluye hashes, timestamp, commit, host.

## Qué NO son los baselines

- **No son ground truth.** El ground truth canónico vive en `evals/fixtures/<case>.expected.json` y es congelado vía proceso de doble revisión médica (`evals/GROUND_TRUTH_PROCESS.md`).
- **No son valores reproducibles exactos.** Claude (y la mayoría de LLMs) operan sin seed determinístico. Re-correr el harness produce números ligeramente distintos cada vez. La invariante que el baseline registra es "todos los gates R0 pasan", no "valor exacto = X".
- **No reemplazan tests.** Los tests del harness viven en `evals/tests/` y operan con MockExtractor. Estos baselines son evidencia empírica con el extractor real, costosa (consumen API), y por tanto no se corren en cada CI.

## Convención de nombres

```
{extractor_model_normalized}_{case_id}.baseline.json
{extractor_model_normalized}_{case_id}.baseline.meta.json
```

Donde:

- `extractor_model_normalized`: modelo + versión separados por guiones bajos (ej. `claude_sonnet_4_5`).
- `case_id`: el mismo identificador que el fixture (ej. `synthetic_case_01`).

Ejemplo: `claude_sonnet_4_5_synthetic_case_01.baseline.json`.

## Estructura del `.meta.json`

Ver `claude_sonnet_4_5_synthetic_case_01.baseline.meta.json` como referencia canónica. Campos requeridos:

| Campo | Descripción |
|---|---|
| `baseline_type` | `"single-run-snapshot"` (futuro: `"multi-run-aggregate"` cuando se promediee sobre múltiples corridas). |
| `baseline_type_notes` | Texto que explica cómo interpretar el baseline. |
| `non_determinism_note` | Aviso explícito sobre que los números no son reproducibles exactos. |
| `report.{path,sha256,size_bytes}` | Hash de integridad del archivo `.baseline.json`. |
| `run.{run_id,timestamp,git_commit,host,platform,python_version}` | Identidad del momento exacto en que se generó. |
| `extractor.{service,version,model,prompt_version}` | Identidad de la pipeline. |
| `pdf_source.{path,sha256,size_bytes}` | Hash del input. Si el PDF cambia, el baseline es inválido. |
| `expected_fixture.{path,sha256}` | Hash del ground truth contra el que se midió. |
| `metrics.{factual_accuracy,critical_omissions,hallucinations,confidence_calibration_error,latency_seconds}` | Valores observados. |
| `r0_gates` | Comparación contra cada umbral de `docs/evaluation/metrics-specification.md`. |
| `command` | Comando exacto que generó el baseline. |
| `related_issues` | Issues que justificaron crear el baseline. |

## Cuándo agregar un nuevo baseline

- Cuando un cambio importante en el extractor (versión nueva, prompt nuevo, modelo nuevo) entra a `main`.
- Cuando un nuevo caso sintético se agrega a `fixtures/` y se quiere registrar el techo de calidad.
- Cuando un dataset real entra y se quiere snapshot del estado actual (baseline va a `baselines/` pero **el PDF NO** — el PDF real vive en object storage privado; el baseline solo contiene métricas, no PHI).

## Cuándo NO agregar un baseline

- Cuando los gates **no pasan** — eso no es un baseline, es evidencia de regresión. Abrir issue.
- Cuando hay PHI en el reporte — los baselines solo pueden contener hashes y métricas, no contenido del caso.
- Para corridas exploratorias o debugging — esas viven en `evals/reports/` (gitignored).

## Comparar baselines

```bash
# Corrida actual vs baseline persistido
python -m sica_evals.cli run --filter <case_id> --extractor clinical --format json
python -m sica_evals.cli diff \
    evals/fixtures/baselines/<baseline>.json \
    evals/reports/<new_run>.json
```

Mostrará deltas por métrica. Deltas grandes negativos = regresión potencial.

## Política de cambio

- **Reemplazar un baseline** requiere PR con justificación: por qué la nueva corrida es la nueva referencia.
- **Borrar un baseline** requiere ADR (raro — solo si la combinación extractor/modelo/prompt fue deprecada).
- **Agregar un baseline** no requiere ADR.

## Referencias

- `docs/evaluation/metrics-specification.md` — definiciones formales de las métricas + umbrales por release.
- `evals/GROUND_TRUTH_PROCESS.md` — proceso de doble revisión médica (genera `expected.json`, no `baseline.json`).
- `docs/decisions/0005-evaluation-methodology.md` — decisiones metodológicas.
- Issue [#9](https://github.com/aaronhuaynate66/sica-platform/issues/9) — primer baseline persistido (este).
