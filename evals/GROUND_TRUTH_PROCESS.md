# Ground Truth Process — SICA Evaluation

**Versión:** 0.1
**Estado:** Borrador operativo. Se ajusta cuando el partner fundador firme y se ejecute la primera ronda real.

Este documento describe el **proceso de doble revisión médica** que produce el ground truth contra el cual `sica-evals` mide la calidad del `clinical-extractor`. Coherente con STRATEGY § 10.4 (synthetic patient testing), § 12.2 (validación clínica retrospectiva) y criterio explícito del issue [#10](https://github.com/aaronhuaynate66/sica-platform/issues/10).

---

## Por qué doble ciego

Si un solo médico produce el ground truth, la métrica de factualidad mide concordancia con esa persona — no con la verdad clínica. Doble ciego con resolución por terceto:

- **Captura desacuerdo médico** como señal (STRATEGY § 10.3 physician disagreement scoring).
- **Reduce sesgo de un solo revisor** (estilo, énfasis, omisiones idiosincráticas).
- **Es el estándar de validación clínica** aceptado por reguladores y revistas (IMDRF § 4.3).

## Roles

| Rol | Responsabilidad | Quién (Fase 1) |
|---|---|---|
| **Revisor A** | Produce ground truth independientemente, ciego al output del modelo y al output del Revisor B. | Obstetra del partner o asesor clínico externo. |
| **Revisor B** | Igual a A, ciego a A y al modelo. | Segundo obstetra. |
| **Árbitro (terceto)** | Resuelve conflictos cuando A y B difieren. Decisión final. | Líder clínico fundador o KOL externo. |
| **Operador del proceso** | Coordina, registra hashes, archiva versiones. No es médico. | Founder / TI del partner. |

`[TODO — confirmar nombres concretos al cerrar partner fundador]`

## Proceso paso a paso

### 1. Selección del caso

- El operador selecciona un PDF clínico desidentificado de `datasets/` (object storage, NUNCA del repo).
- Asigna un `case_id` opaco (`case_NNNN`, sin nombres reales).
- Verifica desidentificación según `docs/security/data-handling.md` § 6 antes de exponerlo a los revisores.

### 2. Briefing a revisores

- Ambos revisores reciben el mismo PDF y el mismo template `ObstetricSummary` para llenar.
- **NO** reciben: el output del modelo, el ground truth previo de otros casos similares, ni se comunican entre sí sobre este caso hasta que ambos firmen.
- Plazo recomendado: 7 días calendario por lote de 10-20 casos.

### 3. Producción independiente

- Revisor A llena `case_NNNN.reviewer_a.json`.
- Revisor B llena `case_NNNN.reviewer_b.json`.
- Ambos almacenados en `ground_truth/raw/` (object storage privado).
- Cada uno firma digitalmente (hash + identidad + timestamp) — formato exacto pendiente, `[TODO]`.

### 4. Comparación automática

- El operador corre un script (futuro, no implementado todavía) que compara A vs B campo por campo usando los mismos comparadores que `sica-evals`.
- Output: `case_NNNN.ab_diff.json` con discrepancias y métrica de concordancia inter-revisor.

### 5. Resolución por terceto

- Si la concordancia A vs B en campos críticos es ≥95%, el ground truth es **`(A + B) merge`** automático (donde ambos coinciden) + reseña rápida del terceto (≤15 min por caso).
- Si la concordancia es <95% en cualquier campo crítico, el terceto:
  - Revisa A, B y el PDF.
  - Decide por campo, justificando en `case_NNNN.arbitration.md`.
  - Firma el ground truth final.

### 6. Publicación del ground truth

- El ground truth final se guarda como `case_NNNN.expected.json` con `case_NNNN.expected.meta.json` indicando:
  - `baseline_type: "double-blind"`
  - `human_reviewer`: IDs opacos de A, B, terceto (no nombres reales si el storage no es estrictamente privado).
  - Hashes de los tres archivos fuente (A, B, arbitraje).
  - Fecha de firma del terceto.
- Almacenado en object storage privado bajo `ground_truth/final/`.
- **NO se commitea al repo.**

### 7. Uso por el harness

- El harness toma `case_NNNN.expected.json` como input (no ve la cadena A/B/arbitraje).
- El reporte resultante referencia `case_NNNN` por ID; no expone los nombres de los revisores.

## Tooling de labeling

Decisión pendiente sobre qué herramienta usar para que los revisores llenen los formularios:

| Opción | Pros | Contras |
|---|---|---|
| **Tool interno custom** (Streamlit / Next.js) | UX clínica específica, sin proveedor externo, integra audit log de SICA. | Requiere construir y mantener. |
| **Label Studio** | Maduro, soporta JSON schema, on-prem instalable. | UX no es clínica; curva de configuración. |
| **Notion / Airtable / Google Forms** | Cero código. | Sin schema validation, riesgo PHI fuera de control. **Descartado** por política. |

`[TODO]` — **Decisión pendiente.** No es trivial: si la decisión final es construir interno, abrir ADR. Si Label Studio gana, documentar el setup en este archivo. Cualquier opción debe respetar `docs/security/data-handling.md` § 4 (RBAC + MFA + audit log).

## Volumen objetivo R0

Coherente con STRATEGY § 7 R0:

- **150-200 historias** retrospectivas desidentificadas → benchmark de extracción.
- **50 casos** de esos 150-200 con ground truth doble-ciego → métricas firmadas.

Los 100-150 restantes se usan para evaluación auto-baseline (output del modelo + verificación heurística) y para entrenamiento si aplica fine-tuning (sujeto a ADR 0004 trigger 1).

## Política de retención del ground truth

- **Tiempo mínimo:** según política del partner + Ley 29733. Ver `docs/security/data-handling.md` § 5.1.
- **Acceso:** RBAC; sólo Revisor A, B, terceto, operador y founder. Auditor externo bajo NDA.
- **Eliminación:** ground truth se elimina junto con el dataset retrospectivo cuando se ejerza derecho del titular (Ley 29733).

## Política de cambio del ground truth

- Una vez firmado por el terceto, el ground truth de un caso **no se modifica** salvo:
  - Error material descubierto post-firma (p. ej. lab que no figuraba en el PDF original).
  - El cambio se registra como **nueva versión** del archivo con su propia firma del terceto. El histórico se preserva.
- **NUNCA** se ajusta el ground truth para "alinear" con el output del modelo. Esto es fraude metodológico.

## Métricas derivadas del proceso

Estas métricas se agregarán al harness en R1+:

- **Inter-rater agreement** (concordancia A vs B por campo, antes del terceto). Señal de qué campos son intrínsecamente subjetivos.
- **Arbitration rate** (% de casos que requirieron resolución del terceto). Señal de calidad del template.
- **Time-to-ground-truth** (tiempo entre PDF asignado y firma del terceto). Señal de viabilidad operativa.

## Auditoría

Cada caso labeled produce un audit trail completo: identidad de A, B, terceto; timestamps; hashes; PDF source; arbitraje si lo hubo. Todo bajo `ground_truth/audit/`. Auditor externo puede reconstruir cualquier caso end-to-end sin acceder al PHI subyacente (las identidades opacas y los hashes son suficientes).

## Referencias

- STRATEGY § 10.3 (physician disagreement scoring), § 10.4 (synthetic patient testing), § 12.2 (validación clínica).
- IMDRF — Software as a Medical Device, clinical evaluation principles.
- `docs/security/data-handling.md` § 4 (acceso) y § 6 (desidentificación).
- `docs/decisions/0003-security-and-phi-policy.md` (política PHI).
- `docs/decisions/0004-model-routing-policy.md` (umbrales de calidad).
- Issue [#10](https://github.com/aaronhuaynate66/sica-platform/issues/10).
- Issue [#5](https://github.com/aaronhuaynate66/sica-platform/issues/5) — acceso a 150-200 historias desidentificadas (bloqueante).
