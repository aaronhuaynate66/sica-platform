---
name: 🐛 Bug Report
about: Reporta un bug reproducible en SICA
title: "[BUG] "
labels: ["bug", "triage"]
assignees: []
---

## Resumen

<!-- Una frase. ¿Qué pasa que no debería pasar? -->

## Pasos para reproducir

1.
2.
3.

## Comportamiento esperado

<!-- Qué debería pasar -->

## Comportamiento observado

<!-- Qué pasa realmente. Incluye output literal, screenshot, o log si aplica. -->

## Entorno

- **Componente afectado** (app, servicio, package): <!-- ej: services/clinical-extractor -->
- **Versión / commit hash**:
- **OS + versión**:
- **Node / Python version** (si aplica):
- **Modelo de IA involucrado** (si aplica): <!-- ej: claude-sonnet-4-5-20250929 -->

## Datos

- [ ] El bug se reproduce con **datos sintéticos** (`evals/fixtures/` o `data/synthetic_*`)
- [ ] El bug solo se reproduce con datos reales (descríbelo abstractamente, **NO pegues PHI**)

## Severidad

- [ ] **Crítico** — afecta seguridad clínica o expone PHI. Ping inmediato al founder.
- [ ] **Alto** — bloquea trabajo o degrada calidad de output clínico.
- [ ] **Medio** — funcionalidad rota pero hay workaround.
- [ ] **Bajo** — molestia, no bloqueante.

## Notas adicionales

<!-- Links, hipótesis de causa raíz, intentos previos de fix. -->
