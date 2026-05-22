# evals/fixtures/ — Casos sintéticos para regression

Esta carpeta contiene **solo casos sintéticos** que el harness de evaluación usa como regression test. No entra PHI real aquí — eso vive en object storage privado (ver `evals/GROUND_TRUTH_PROCESS.md` y `docs/security/data-handling.md`).

## Convenciones de naming

Por cada caso, tres archivos pueden coexistir:

| Archivo | Obligatorio | Contenido |
|---|:---:|---|
| `{case_id}.pdf` | Recomendado | PDF sintético del caso (si está en `services/clinical-extractor/data/` el path canónico va en `.expected.meta.json`). |
| `{case_id}.expected.json` | **Sí** | Output esperado en formato `ObstetricSummary`. |
| `{case_id}.expected.meta.json` | Recomendado | Metadatos: tipo de baseline, revisor humano, hash del PDF, modelo que lo generó, fecha. |

`case_id` debe ser estable, kebab/snake case, sin PHI ni nombres reales. Ejemplos: `synthetic_case_01`, `preeclampsia_atypical_01`, `gemelar_discordant_growth`.

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
