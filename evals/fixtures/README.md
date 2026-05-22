# evals/fixtures/ — Casos sintéticos para regression

Esta carpeta contiene **solo casos sintéticos** que el harness de evaluación usa como regression test. No entra PHI real aquí — eso vive en object storage privado (ver `evals/GROUND_TRUTH_PROCESS.md` y `docs/security/data-handling.md`).

## Casos disponibles

| case_id | Tipo clínico | Notas | Confidence esperada |
|---|---|---|:---:|
| `synthetic_case_01` | Control normal G2P1, EG 28 sem | Caso baseline original (issue #9). Cesárea previa + anemia leve. | 0.95 |
| `synthetic_case_02_preeclampsia` | Preeclampsia severa, EG 32 sem | Plaquetopenia + proteinuria + plan con sulfato de Mg. | 0.92 |
| `synthetic_case_03_gemelar` | Embarazo gemelar bicorial biamniótico, EG 24 sem | Corionicidad confirmada eco 12 sem. | 0.90 |
| `synthetic_case_04_rpm` | RPM pretérmino, EG 34 sem | Sin signos de corioamnionitis. Manejo expectante. | 0.92 |
| `synthetic_case_05_diabetes_gestacional` | DG con macrosomía estimada, EG 28 sem | Curva TOG anormal en 3 puntos + HbA1c 6.4%. | 0.93 |
| `synthetic_case_06_anemia_severa` | Anemia ferropénica severa, EG 30 sem | Hb 7.2 sintomática — hierro EV + reevaluar transfusión. | 0.92 |
| `synthetic_case_07_manuscrito` | Control normal, EG 22 sem, PDF con ruido OCR | Mismo perfil clínico que case_01 pero el PDF emula manuscrito digitalizado con sustituciones de caracteres (l↔1, O↔0, Z↔2, etc.). Stress-test del extractor frente a OCR ruidoso. | 0.72 |

Todos los PDFs canónicos viven en `services/clinical-extractor/data/` y se copian aquí para que el harness los encuentre sin depender del path canónico.

Generador: `services/clinical-extractor/scripts/generate_synthetic_pdfs.py` (regenerable, determinista en contenido — bytes pueden cambiar por timestamps internos de reportlab).

## Cuándo agregar más casos

Agregar un caso sintético tiene sentido cuando:

1. **Cobertura clínica falta**: un escenario relevante para el wedge R1/R2 (obstetricia + neonatal) que ninguno de los actuales ejercita — p. ej. preeclampsia atípica sin proteinuria, síndrome HELLP, preeclampsia post-parto, RPM con corioamnionitis franca, restricción de crecimiento intrauterino.
2. **Modo de fallo nuevo**: un patrón de PDF/OCR que rompió al extractor en producción y queremos prevenir regresión (PDF escaneado torcido, tabla con merged cells, abreviaturas locales no estándar).
3. **Issue específico lo demanda**: el comparador o una métrica nueva necesita un caso que la ejercite (ej. evaluación de razonamiento temporal — STRATEGY § 10.1 pilar 6).

**No** agregar casos solo para inflar el conteo. Cada caso es regression test permanente; mantener fixture, meta, schema y ground truth alineados tiene costo.

Casos curados por médicos reales (single-reviewer o double-blind) **reemplazan** a los sintéticos en categorías solapadas — no se acumulan.

## Convenciones de naming

Por cada caso, tres archivos pueden coexistir:

| Archivo | Obligatorio | Contenido |
|---|:---:|---|
| `{case_id}.pdf` | Recomendado | PDF sintético del caso (si está en `services/clinical-extractor/data/` el path canónico va en `.expected.meta.json`). |
| `{case_id}.expected.json` | **Sí** | Output esperado en formato `ObstetricSummary`. |
| `{case_id}.expected.meta.json` | Recomendado | Metadatos: tipo de baseline, revisor humano, hash del PDF, modelo que lo generó, fecha. |

`case_id` debe ser estable, kebab/snake case, sin PHI ni nombres reales.

Convención adoptada en el dataset actual: `synthetic_case_NN_descripcion` donde `NN` es el número correlativo y `descripcion` el patrón clínico dominante (`preeclampsia`, `gemelar`, `rpm`, `diabetes_gestacional`, `anemia_severa`, `manuscrito`). Para casos curados por médicos reales — sin numeración correlativa: `preeclampsia_atypical_01`, `gemelar_discordant_growth`, etc.

## Estructura de `expected.json`

Debe validar contra `ObstetricSummary` de `services/clinical-extractor/src/clinical_extractor/schemas.py`. Campos esperados (ver schema canónico para tipos completos):

```jsonc
{
  "patient_age": 32,
  "gestational_age_weeks": 28.3,
  "fum": "2025-09-15",                   // ISO date
  "fpp": "2026-06-22",
  "active_problems": ["..."],
  "risk_factors": ["..."],
  "lab_results": [
    {
      "name": "Hemoglobina",
      "value": "10.8",
      "unit": "g/dL",
      "date": "2026-04-02",
      "abnormal": true                  // true marca el lab como "crítico"
    }
  ],
  "notes_summary": "...",
  "confidence_score": 0.95,             // 0..1
  "evidence_spans": [
    { "claim": "...", "source_page": 1, "source_text": "..." }
  ]
}
```

Valores `null` o ausentes son válidos (no es lo mismo que vacíos). El comparador distingue `None` esperado vs. valor producido (=> `hallucinated`) de `None` actual vs. esperado (=> `missing`).

## Estructura de `expected.meta.json`

Schema actual (ver `synthetic_case_01.expected.meta.json` como ejemplo):

```jsonc
{
  "baseline_type": "non-clinical" | "double-blind" | "single-reviewer",
  "baseline_type_notes": "...",         // texto explicando la fuente del ground truth
  "created_at": "2026-05-21T04:37:54Z", // ISO timestamp
  "fixture": {
    "path": "evals/fixtures/synthetic_case_01.expected.json",
    "sha256": "...",
    "size_bytes": 3335
  },
  "human_reviewer": null,               // ID/iniciales del médico (o null si no aplica)
  "model": "claude-sonnet-4-5-20250929",
  "non_determinism_note": "...",
  "pdf_source": {
    "path": "services/clinical-extractor/data/synthetic_case_01.pdf",
    "sha256": "...",
    "size_bytes": 5626
  },
  "produced_by": {
    "command": "...",
    "extractor_version": "0.1.0",
    "service": "clinical-extractor"
  },
  "prompt_version": "0.1.0",
  "related_issues": ["#9"],
  "schema_version": "ObstetricSummary v0"
}
```

## Tipos de baseline (`baseline_type`)

| Valor | Significado | Cuándo usarlo |
|---|---|---|
| `non-clinical` | Generado por modelo + revisión heurística, sin firma médica. | Smoke tests de pipeline. **No** valida calidad clínica. |
| `single-reviewer` | Un solo médico produjo o validó el output esperado. | Casos sintéticos curados por un clínico. Aceptable para R0 si está marcado. |
| `double-blind` | Dos médicos generaron ground truth independientemente, terceto resolvió diferencias. | **Requerido** para baselines reales del partner. Ver `GROUND_TRUTH_PROCESS.md`. |

## Cuándo agregar `human_reviewer`

- **Siempre** cuando `baseline_type` es `single-reviewer` o `double-blind`.
- **Nunca** con nombre real del médico si el repo es público — usar iniciales o ID opaco (p. ej. `MR-001`).
- `null` solo para `non-clinical`.

## Política de cambio

- **Cambiar el contenido de un `expected.json` requiere ADR** si se hace para "alinear" con el extractor (eso anula el valor del test).
- **Agregar un caso nuevo** no requiere ADR; sí requiere PR con review.
- **Borrar un caso** requiere justificación en el PR (qué reemplaza la cobertura que se pierde).

## Verificar un fixture localmente

```bash
cd evals
python -m sica_evals.cli run --filter {case_id} --format markdown --extractor mock
```

`--extractor mock` devuelve el `expected.json` tal cual, por lo que el resultado debería ser perfecto (factual_accuracy=1.0). Si no lo es, hay un bug en el comparador o en el fixture.

Para validar contra el extractor real:

```bash
cd evals
python -m sica_evals.cli run --filter {case_id} --extractor clinical --format markdown
```

Esto consume API key y dinero. No correr en CI sin gate explícito.
