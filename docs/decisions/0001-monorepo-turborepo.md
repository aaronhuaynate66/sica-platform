# 0001. Monorepo en `sica-platform` con Turborepo + pnpm

- **Status:** Accepted
- **Date:** 2026-05-20
- **Deciders:** Aaron Huaynate (founder / CTO)
- **Tags:** infra, dx, monorepo, build-system

## Context

SICA arranca Fase 2 (construcción) en mayo 2026. Mirando 18 meses adelante, el sistema tendrá al menos:

- **Frontends**: panel clínico alpha (R1), embed para HIS (R2), vista neonatal (R3), brief preanestésico (R4), módulo CRED (R5), harness web para labeling de ground truth, dashboards de calidad.
- **Servicios Python**: `clinical-extractor` (PDFs → FHIR), orquestador clínico (LangGraph), pipeline de evals (DSPy), conectores HL7v2 / FHIR, OCR wrapper.
- **Packages compartidos TS**: tipos FHIR, componentes UI clínicos (timeline, evidencia trazable, badges de confianza), eval SDK, clientes de servicios.
- **Configuración cruzada**: prompt registry versionado, fixtures de evaluación, esquemas FHIR, políticas de routing de modelos.

Necesitamos decidir **ahora** dónde vive todo esto, porque la elección condiciona DX y velocidad por los próximos 18 meses. Decidir tarde es caro: mover código entre repos después de tener 50 PRs activos rompe historia, autoría y CI.

Restricciones de SICA que pesan:

1. **Cambios atómicos cross-stack.** Cambiar un campo de `ObstetricSummary` toca: schema Pydantic en `clinical-extractor`, tipo TS en frontend, prompt en el orquestador, fixture en evals, y validación de UI. Si esos viven en 5 repos, el cambio se vuelve 5 PRs coordinados — y la coordinación es donde se introducen bugs clínicos silenciosos.
2. **Equipo pequeño** (founder + 1–2 builders early). No hay ancho de banda para mantener cinco pipelines de CI, cinco changelogs, cinco versionings.
3. **Auditabilidad regulatoria.** STRATEGY § 13 + § 10.7 piden audit trail end-to-end. Tener "qué versión del prompt corrió en qué deploy" trazado en un commit único es mucho más simple que reconstruirlo a través de submodules.
4. **Rotación de tooling.** Sospechamos que vamos a probar varias librerías de eval (DSPy, Promptfoo, custom) y varios frameworks UI antes de R2. Un monorepo permite swap sin re-bootstrap de infra.

## Decision

**SICA usa un monorepo único** en el repositorio `sica-platform`, con dos sistemas coexistiendo:

- **Workspace TS/JS**: gestionado con **pnpm workspaces** (`apps/*`, `packages/*`) y orquestado con **Turborepo** para builds, lint y test incrementales con cache.
- **Servicios Python**: cada uno en `services/<nombre>/` con su propio `pyproject.toml`, virtualenv local, y configuración de Ruff + mypy. Sin workspace Python compartido por ahora — la sobrecarga de uno (uv workspace o Poetry monorepo) no se justifica con un solo servicio.

Estructura raíz:

```
sica-platform/
├── apps/         ← Next.js apps
├── packages/     ← TS packages compartidos
├── services/     ← Servicios Python (clinical-extractor, ...)
├── evals/        ← Suite de evaluación clínica
├── docs/         ← Estrategia, roadmap, ADRs
└── .github/      ← Workflows + templates
```

Las dependencias se versionan en `package.json` raíz para devDeps comunes (turbo, prettier), y por subpaquete para deps de runtime. Los servicios Python son **completamente independientes** entre sí — sin imports cruzados — y exponen API HTTP cuando necesitan colaborar.

## Consequences

### Positive

- **Cambios atómicos**: un PR puede tocar schema Pydantic, tipo TS y fixture de eval en el mismo commit. Reviewer ve el cambio completo.
- **Refactor seguro**: rename de un símbolo cross-package se hace en una operación, sin coordinar versiones publicadas.
- **CI/CD único**: un workflow por tipo de tarea (lint-node, lint-python, eval-regression). Configurar GitHub Actions una vez.
- **Audit trail simple**: `git log` da la historia completa de SICA. Para regulación peruana esto importa — un solo commit hash identifica el estado del producto.
- **Onboarding rápido**: `git clone && pnpm install` y un nuevo dev ve todo el sistema. Sin hunt por repos privados separados.
- **Turborepo cache local + remoto**: builds incrementales reales. Cambiar un archivo en `apps/clinical-panel` no rebuilds `services/clinical-extractor`.

### Negative

- **Repo crece**: en 18 meses el repo va a ser más grande que repos típicos single-purpose. Mitigación: shallow clones para CI, `.gitignore` agresivo con datos clínicos, separación clara `docs/` vs código.
- **Permisos all-or-nothing**: cualquiera con acceso al repo ve todo. Mitigación: acceso al repo es decisión deliberada del founder hasta que haya >5 contributors; si llegamos a ese tamaño revisamos.
- **CI matrix más compleja**: hay que poner paths-filter para que un cambio en `docs/` no dispare lint Python. Manejable con `dorny/paths-filter` o filtros nativos de GitHub Actions.
- **Lock-in mental al monorepo**: en un año, separar `clinical-extractor` a su repo si lo open-sourceamos cuesta trabajo manual. Aceptado: optimizamos por velocidad de desarrollo ahora, no por reversibilidad ideal.
- **Tooling Python no monorepo-nativo**: pip / poetry / uv no entienden workspaces como pnpm. Solución: cada servicio Python es self-contained, no compartimos código Python por ahora.

## Alternatives considered

### Alternativa A: Multi-repo (un repo por servicio + app)

**Forma**: `sica-strategy`, `sica-clinical-extractor`, `sica-clinical-panel`, `sica-eval-harness`, etc.

**Por qué no:**
- Cambio cross-stack obliga a coordinar N PRs. Para un equipo de 1–3 personas esto es overhead puro.
- Versionado: cada paquete TS que se consume cross-repo necesita publicación a un registry (npm privado o GitHub Packages). El primer mes se nos va configurando esto.
- Audit trail se rompe: "¿qué versión del extractor corrió con qué prompt el 15 de junio?" requiere consultar 3 repos.
- Beneficio teórico (permisos granulares, deploys independientes) no se materializa hasta que el equipo es ≥10. Estamos en 1.

### Alternativa B: Nx monorepo

**Forma**: monorepo con Nx en lugar de Turborepo.

**Por qué no:**
- Nx tiene mejor generación de scaffolding y un grafo de dependencias más sofisticado, pero su modelo opinado (plugins, `nx.json`, generators) tiene una curva más empinada y resta velocidad en las primeras semanas.
- Turborepo es deliberadamente simple: un `turbo.json`, pipelines declarativas, cache local. Para nuestro tamaño es suficiente.
- Nx tiene mejor soporte cross-language (Angular, NestJS, etc.) pero nuestro mix es Next.js + Python — y Python no se integra bien con Nx tampoco.
- Si en 12 meses necesitamos lo que Nx ofrece (afected graphs sofisticados, generators custom), migrar Turborepo → Nx no es trivial pero es factible. Hoy no se justifica el costo.

### Alternativa C: pnpm puro sin Turborepo

**Forma**: workspaces de pnpm sin un orquestador de builds.

**Por qué no:**
- pnpm workspaces resuelve **instalación** y **link interno**, pero no orquesta **builds incrementales** ni cache. Sin esto, `pnpm -r run build` recompila todo cada vez.
- En cuanto haya 2+ apps + 3+ packages, esto se vuelve doloroso (minutos perdidos en cada CI run).
- Turborepo es liviano (un archivo de config) y aporta cache local + remoto desde el día uno.

### Alternativa D: Lerna

**Forma**: Lerna como orquestador.

**Por qué no:**
- Lerna fue muy popular 2017–2021 y entró en modo mantenimiento. Vercel mantiene Turborepo activamente y absorbió a Nx-ish features.
- Para nuevos proyectos en 2026, Turborepo o Nx son la elección por default; Lerna no aporta nada que no esté cubierto.

### Alternativa E: Bazel / Pants / Buck

**Forma**: build system al estilo Google.

**Por qué no:**
- Sobredimensionado. Estos shine en repos de >100 ingenieros con builds heterogéneos masivos. Para un equipo de 1–3 son meses de yak-shaving sin ROI.
- Setup time mata velocidad temprana. Volveríamos a evaluar si llegamos a 30+ devs.

## References

- [Turborepo docs](https://turbo.build/repo/docs)
- [pnpm workspaces](https://pnpm.io/workspaces)
- [MADR — Markdown ADR template](https://adr.github.io/madr/)
- Casos de referencia: **Vercel** (monorepo público con Turborepo), **Linear** (monorepo con Turborepo, foundational a su DX story), **Stripe** (monorepo masivo con tooling custom), **Shopify** (monorepo con Bazel + custom), **t3-oss/create-t3-turbo** (template comunitario de referencia).
- STRATEGY.md § 11 (arquitectura técnica), § 13 (regulatorio peruano y audit), § 10.7 (operación continua de evals).
- docs/roadmap.md — R0 Foundation requiere stack mínimo reproducible.

## Revisión

Esta decisión se revisa explícitamente en uno de estos triggers:

- El equipo supera 5 contributors activos.
- Necesitamos open-sourcear un módulo (típicamente `clinical-extractor` o `eval-sdk`).
- Hay un servicio Python que requiere acceso muy distinto al resto (ej. on-prem en clínica).

Hasta entonces, **monorepo + Turborepo + pnpm** es la elección.
