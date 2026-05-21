---
name: 🩺 Clinical Validation
about: Issue específico para validación clínica de un output o capacidad de SICA
title: "[CLIN] "
labels: ["clinical-validation", "needs-physician-review"]
assignees: []
---

> **Nota:** este template se usa para issues donde un médico debe revisar un output del sistema y dejar veredicto trazable. Es uno de los artefactos críticos para el Clinical Data Flywheel (STRATEGY § 9) y para la Eval Infrastructure (STRATEGY § 10).

## Caso de uso

<!--
¿Qué capacidad estamos validando?
Ej: "Resumen obstétrico longitudinal sobre paciente con cesárea previa + anemia + GBS desconocido"
-->

- **Capacidad** (STRATEGY § 6): <!-- ej: Memory Graph + Reasoning Engine -->
- **Release**: <!-- R0 / R1 / R2 / R3 / R4 / R5 -->
- **Especialidad**: <!-- obstetricia / neonatología / pediatría / anestesia -->

## Dataset

- **Origen**: <!-- sintético | retrospectivo desidentificado | partner X -->
- **Tamaño**: <!-- N casos -->
- **Ruta** (si aplica): <!-- evals/fixtures/<set>/ o referencia interna SIN PHI en el issue -->
- **Versión / hash del dataset**:

## Modelo y prompt

- **Modelo**: <!-- claude-sonnet-4-5-20250929, medgemma-4b, gemini-2.5-flash, etc. -->
- **Prompt version**: <!-- hash o tag del prompt usado -->
- **Pipeline / servicio**: <!-- clinical-extractor v0.x, orquestador R2, etc. -->

## Métrica esperada

<!--
Antes de pedir revisión, define la métrica.
Ej:
- Factualidad span-level >= 85%
- Omisiones críticas <= 5%
- Tasa de hallucination = 0 en este subset
-->

| Métrica | Meta | Resultado actual |
|---|---:|---:|
|  |  |  |

## Médico revisor

- **Nombre**:
- **Especialidad / cargo**:
- **Institución** (si aplica):
- **Fecha programada de revisión**:
- **Modalidad**: <!-- async (formulario) | sesión sincrónica | doble ciego con otro médico -->

## Hallazgos

<!--
A completar por el revisor. Categorización de cada problema encontrado según
STRATEGY § 10.3 (physician disagreement scoring):
-->

### Factual fixes (hechos incorrectos)
- [ ] Caso ID — descripción
-

### Critical additions (omisiones críticas)
- [ ] Caso ID — descripción
-

### Style edits (redacción)
-

### Emphasis edits (ordenamiento / destaque)
-

### Removals (verbosidad / irrelevante)
-

### Hallucinations (información inventada)
- [ ] Caso ID — descripción
-

## Veredicto

- [ ] **Acepta para producción** (cumple métrica)
- [ ] **Requiere iteración** (no cumple métrica — describir gaps abajo)
- [ ] **Bloqueador clínico** (riesgo de seguridad — escalado inmediato)

## Acciones derivadas

<!-- Tickets de seguimiento, fix de prompt, retraining, nuevo eval set, etc. -->

- [ ] Linkar issues / PRs:
- [ ] Actualizar prompt registry:
- [ ] Agregar casos a regression set:

## Firma del revisor

Al cerrar este issue, el médico revisor confirma que la información de hallazgos refleja su revisión. Este issue es **artefacto regulatorio** y se conserva en historia.

- **Revisor**:
- **Fecha de firma**:
