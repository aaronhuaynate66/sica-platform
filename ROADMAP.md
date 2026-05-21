# Roadmap SICA

> Documento vivo. Se regenera automáticamente cada vez que cambian los issues en GitHub.  
> Última actualización (derivada de issues): `2026-05-21T05:13:14Z`  
> Generado por: [`.github/workflows/sync-roadmap.yml`](.github/workflows/sync-roadmap.yml)  
> No editar manualmente — los cambios se sobrescriben en el siguiente run.


## Estado actual

- **Release activo:** R0 Foundation (Mes 0–2)
- **Issues totales:** 15
- **Bloqueantes abiertos:** 4
- **Progreso R0:** 1 de 9 cerrados (11%)

## Visión a 18 meses

| Release | Mes | Wedge | Gate de salida |
|---|---|---|---|
| R0 Foundation | 0–2 | Benchmark + stack mínimo, sin UI clínica | MedGemma 4B ≥85% factualidad, ≤5% omisiones críticas |
| R1 Resumen Obstétrico (Alpha) | 2–5 | Panel standalone, sesiones de revisión | >70% resúmenes útiles sin edición mayor |
| R2 Shadow + Checklist | 5–8 | Embed en HIS, sin uso mandatorio | ≥40% uso + recall brechas ≥80% + 0 incidentes seguridad |
| R3 Handoff Materno-Neonatal | 8–11 | Primer flujo crítico (asistivo) | Completitud ≥95% + correcciones <10% + aprobación neo |
| R4 Brief Preanestésico | 11–14 | Cesárea programada y urgencia | <10% correcciones críticas + aprobación calidad |
| R5 CRED + Multi-sede | 14–18 | Pediatría longitudinal + producto replicable | Sede 2 onboarded + renovación partner |

Fuente detallada: [`docs/roadmap.md`](docs/roadmap.md).

## Release activo: R0 Foundation

**Período:** Mes 0–2  
**Wedge:** Benchmark + stack mínimo, sin UI clínica  
**Gate de salida:** MedGemma 4B ≥85% factualidad, ≤5% omisiones críticas

### Issues abiertos en R0

- [ ] **[#15](https://github.com/aaronhuaynate66/sica-platform/issues/15)** [R0] Documentar políticas de seguridad y manejo de PHI antes del primer dato real
- [ ] **[#14](https://github.com/aaronhuaynate66/sica-platform/issues/14)** [R0] Setup de Langfuse self-hosted o decisión de servicio gestionado
- [ ] **[#13](https://github.com/aaronhuaynate66/sica-platform/issues/13)** [R0] Crear primer ADR sobre política de routing de modelos (MedGemma vs Gemini vs Claude)
- [ ] **[#12](https://github.com/aaronhuaynate66/sica-platform/issues/12)** [R0] Investigar viabilidad de MedGemma 4B local en el entorno del partner
- [ ] **[#11](https://github.com/aaronhuaynate66/sica-platform/issues/11)** [R0] Definir métricas de factualidad: span-level accuracy + critical omissions
- [ ] **[#10](https://github.com/aaronhuaynate66/sica-platform/issues/10)** [R0] Diseñar el harness de evaluación: dataset retrospectivo + ground truth process
- [ ] **[#9](https://github.com/aaronhuaynate66/sica-platform/issues/9)** [R0] Validar pipeline clinical-extractor en synthetic_case_01
- [ ] **[#5](https://github.com/aaronhuaynate66/sica-platform/issues/5)** [DATA] Acceso a 150-200 historias obstétricas desidentificadas para benchmark R0 · `bloqueante` `data`

### Issues cerrados en R0

- [x] ~~**[#8](https://github.com/aaronhuaynate66/sica-platform/issues/8)** [R0] Setup técnico del monorepo~~ · cerrado 2026-05-21

### Bloqueadores activos

- 🚧 **[#5](https://github.com/aaronhuaynate66/sica-platform/issues/5)** [DATA] Acceso a 150-200 historias obstétricas desidentificadas para benchmark R0 · `data` `r0`
- 🚧 **[#4](https://github.com/aaronhuaynate66/sica-platform/issues/4)** [GTM] Confirmar partner fundador (clínica privada materno-infantil en Lima) · `gtm`
- 🚧 **[#2](https://github.com/aaronhuaynate66/sica-platform/issues/2)** [LEGAL] Validar plan de protección de datos (Ley 29733): banco, DPIA, DPO, consentimientos · `legal`
- 🚧 **[#1](https://github.com/aaronhuaynate66/sica-platform/issues/1)** [REGULATORIO] Validar clasificación de SICA como software asistivo no dispositivo médico · `regulatorio`

## Siguiente release: R1 Resumen Obstétrico (Alpha)

**Período:** Mes 2–5  
**Estado:** Pendiente. Arranca cuando R0 cierre gate.  
**Gate de salida:** >70% resúmenes calificados útiles sin edición mayor.

## Issues por categoría

### Regulatorio y Legal

- [ ] **[#3](https://github.com/aaronhuaynate66/sica-platform/issues/3)** [MARCA] Verificar marca SICA en Indecopi · `marca`
- [ ] **[#2](https://github.com/aaronhuaynate66/sica-platform/issues/2)** [LEGAL] Validar plan de protección de datos (Ley 29733): banco, DPIA, DPO, consentimientos · `bloqueante`
- [ ] **[#1](https://github.com/aaronhuaynate66/sica-platform/issues/1)** [REGULATORIO] Validar clasificación de SICA como software asistivo no dispositivo médico · `bloqueante`

### GTM y Distribution

- [ ] **[#7](https://github.com/aaronhuaynate66/sica-platform/issues/7)** [GTM] Identificar 5 KOLs target para Distribution Engine
- [ ] **[#4](https://github.com/aaronhuaynate66/sica-platform/issues/4)** [GTM] Confirmar partner fundador (clínica privada materno-infantil en Lima) · `bloqueante`

### Datos y Eval

- [ ] **[#6](https://github.com/aaronhuaynate66/sica-platform/issues/6)** [MERCADO] Análisis competitivo Perú/LatAm con field research · `mercado`
- [ ] **[#5](https://github.com/aaronhuaynate66/sica-platform/issues/5)** [DATA] Acceso a 150-200 historias obstétricas desidentificadas para benchmark R0 · `bloqueante` `r0`

### Mercado

- [ ] **[#6](https://github.com/aaronhuaynate66/sica-platform/issues/6)** [MERCADO] Análisis competitivo Perú/LatAm con field research · `investigacion`

### Marca

- [ ] **[#3](https://github.com/aaronhuaynate66/sica-platform/issues/3)** [MARCA] Verificar marca SICA en Indecopi · `legal`

## Cómo se actualiza este documento

Este archivo se regenera automáticamente cada vez que:

- Se abre, cierra o edita un issue
- Se agregan o quitan labels a un issue
- Se mergea un PR a `main`
- Una vez al día por cron (safety net)
- Se dispara manualmente desde Actions (`workflow_dispatch`)

**No editar manualmente.** Si necesitás reflejar algo acá, hacelo cambiando los issues correspondientes en GitHub (estado, labels, título). El próximo run del workflow lo recoge.

Si el workflow necesita desactivarse temporalmente, ver [ADR 0002](docs/decisions/0002-living-roadmap-system.md).

- Última generación (derivada del issue updatedAt más reciente): `2026-05-21T05:13:14Z`
- Commit que la generó: `<sin corrida previa>`
