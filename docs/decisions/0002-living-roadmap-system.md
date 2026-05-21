# 0002. Living Roadmap System: `ROADMAP.md` auto-sincronizado desde issues

- **Status:** Accepted
- **Date:** 2026-05-21
- **Deciders:** Aaron Huaynate (founder / CTO)
- **Tags:** infra, dx, governance, project-management, automation
- **Related:** [ADR 0001](0001-monorepo-turborepo.md) (monorepo + Turborepo)

## Context

SICA tiene tres lugares donde vive información sobre el estado del trabajo:

1. **`STRATEGY.md`** y **`docs/roadmap.md`** — documentos estratégicos editados manualmente, fuente de verdad de la visión 18 meses.
2. **GitHub issues** — unidades operativas de trabajo: bugs, features, tareas R0, validaciones clínicas, decisiones pendientes.
3. **GitHub Project "SICA Roadmap"** ([#2](https://github.com/users/aaronhuaynate66/projects/2)) — kanban visual sobre los issues.

Entre estos tres hay un hueco: **¿qué pasa cuándo, sin abrir GitHub o sin ser técnico, querés saber en qué estado está el roadmap operativo?** Hoy hay que:

- Abrir GitHub
- Filtrar issues por label `r0`
- Contar abiertos y cerrados manualmente
- Cruzar con `docs/roadmap.md` para entender el gate de salida

Eso no escala. Cuando haya inversores, asesores clínicos, KOLs o miembros nuevos del equipo mirando el repo, necesitan **una sola página, en la raíz, navegable, que refleje el estado real**. Esa página es `ROADMAP.md`.

El problema con `ROADMAP.md` editado a mano es el mismo de cualquier documento de status manual: se desactualiza en cuanto el ritmo de issues sube. La única forma de mantenerlo confiable a largo plazo es **regenerarlo desde la fuente** (GitHub issues) y dejar que los humanos solo lo lean.

## Decision

Implementar un **Living Roadmap System** con tres piezas conectadas:

### Pieza 1: `ROADMAP.md` en la raíz del repo
Documento Markdown navegable, generado automáticamente. Se commitea al repo (no es artefacto de CI) para que sea visible en la home del repo en GitHub sin necesidad de hacer click.

### Pieza 2: `scripts/generate_roadmap.py`
Script Python stdlib-only (sin dependencias externas) que:
- Lee issues via `gh issue list --json ...`
- Renderiza `ROADMAP.md` desde un template embebido
- Es **determinístico**: misma data → mismo output bit-exacto (el timestamp del documento se deriva del `updatedAt` máximo entre issues, **no** de `now()`)
- Es **idempotente**: si el output coincide con el archivo en disco, no se reescribe
- Tiene modo `--check` para validar en PRs que el documento está al día

### Pieza 3: `.github/workflows/sync-roadmap.yml`
GitHub Action que dispara con:
- Eventos de `issues` (opened, closed, reopened, labeled, unlabeled, edited)
- `pull_request: closed` cuando se mergea a `main`
- `workflow_dispatch` (botón manual en Actions)
- `schedule: cron "0 13 * * *"` (13:00 UTC, una vez al día — safety net si un evento se perdió)

El job corre el script, detecta si `ROADMAP.md` cambió (`git diff --quiet`), y **solo si cambió** commitea + pushea con identidad de bot.

### Identidad del bot

Commits del workflow van con:

```
Author: sica-bot[bot] <sica-bot@users.noreply.github.com>
```

**deliberadamente distinto** de cualquier humano del equipo.

## Consequences

### Positive

- **Una fuente de verdad operativa.** El estado real vive en issues; `ROADMAP.md` es la proyección legible. No hay riesgo de divergencia porque no se edita a mano.
- **Onboarding instantáneo.** Quien entre al repo ve en la home: estado actual, qué está en R0, qué bloqueadores hay, qué viene después.
- **Filtro limpio del git log humano.** Como el bot usa identidad propia, `git log --author=ahuaynate` (o cualquier humano) excluye automáticamente los commits de sync. La historia de cambios humanos queda separada del ruido de auto-sync.
- **Audit trail completo del estado.** Cada cambio del roadmap queda como un commit del bot con fecha y diff. Si en seis meses queremos saber cuándo se cerró tal bloqueador, el git log lo muestra exactamente.
- **Sin dependencias externas.** Stdlib + `gh` CLI. No hay riesgo de que se rompa por un breaking change de una librería de terceros, ni costo de mantener un Dockerfile especial.
- **Determinismo garantizado.** El script no escribe el archivo si el contenido no cambió. El workflow no commitea si el archivo no cambió. Ambos check independientes. Resultado: cero commits espurios.
- **Trigger por GitHub Token no causa loops.** Por safety nativa de GitHub Actions, un push hecho con `GITHUB_TOKEN` no dispara otros workflows. El commit del bot no re-dispara sync-roadmap ni CI.

### Negative

- **Commits de bot en el log.** Cada vez que alguien edita un issue, va a haber un commit del bot. Para repos con alto volumen de tickets esto se puede notar en `git log`. **Mitigación:** el bot tiene email propio, así que `git log --invert-grep --author=sica-bot` muestra solo humanos. Convención recomendada cuando hagamos blame: filtrar por author.
- **Latencia hasta que el ROADMAP refleje un cambio.** El workflow tarda ~30–60 segundos en correr y commitear. Si alguien acaba de etiquetar un issue, el `ROADMAP.md` remoto va a estar desactualizado por menos de un minuto. Aceptado.
- **Dependencia de `gh` CLI estando disponible.** En `ubuntu-latest` viene preinstalado. Si GitHub cambia el runner default, hay que verificar.
- **El template del ROADMAP vive en código Python.** Cambiar la estructura del documento requiere editar `scripts/generate_roadmap.py`. **Aceptado** porque es Python directo y legible (no Jinja, no f-strings opacos a gran escala). Cambios al template requieren PR humano, no se generan por sí solos.
- **Rate limiting de `gh` CLI.** El script hace una sola llamada `gh issue list`. Cron diario + eventos = ~50 corridas/día máximo en condiciones normales. Muy lejos del límite de GitHub API (5000/hora).
- **Falsa sensación de actualidad.** Que el documento exista no significa que las decisiones detrás de los issues estén bien. El ROADMAP es proyección del estado de tickets, no validación de que los tickets reflejen la realidad. **Convención:** la realidad estratégica vive en `STRATEGY.md`; el ROADMAP es operativo.

## Alternatives considered

### Alternativa A: Editar `ROADMAP.md` a mano cuando sea necesario

**Por qué no:**
- Se desactualiza en la primera semana ocupada.
- Genera fricción mental ("¿tengo que actualizar el roadmap también?") que se evita o se hace mal.
- No escala más allá de un equipo de 1.
- Es exactamente el problema que el living roadmap resuelve.

### Alternativa B: No tener `ROADMAP.md` en absoluto, solo Project + issues

**Por qué no:**
- Requiere que cualquier visitante del repo abra GitHub, navegue al Project, entienda las columnas. No funciona para asesores no técnicos ni para inversores que escanean el repo en GitHub.
- La home del repo es la primera impresión. Tener un `ROADMAP.md` en raíz que se renderiza inline en la página principal es valor sin costo recurrente.

### Alternativa C: Usar una herramienta SaaS (Linear, ProductBoard, Notion)

**Por qué no:**
- Agrega dependencia externa para algo que GitHub Issues ya hace bien.
- Costo mensual para algo que con un workflow es gratis.
- Para Fase 1 con un equipo pequeño no hace falta. Si pasamos a 5+ contributors y la complejidad crece, revisamos.
- Pierde la integración con el repo (issues, commits, PRs en el mismo lugar).

### Alternativa D: GitHub Pages con un dashboard custom

**Por qué no:**
- Es la versión "rica" de esto, con cargas adicionales: hosting estático, build pipeline, posiblemente JS, posiblemente accesibilidad a auditar. Para R0 es overkill.
- `ROADMAP.md` se renderiza bien en GitHub directamente y es suficiente para Fase 1.
- Si en R3+ queremos un dashboard de calidad clínica o uso por médico, eso será un app dedicado, no un extension de este sistema.

### Alternativa E: Cron-only (sin triggers de issues)

**Por qué no:**
- Latencia de actualización sube de minutos a horas/día.
- Cambios importantes (cerrar un bloqueante) no se reflejan hasta el próximo cron. Mata el sentido de "living".
- El cron diario se mantiene **como safety net** además de los triggers de issue, no en lugar de ellos.

## Cómo desactivar el workflow si llega a ser problemático

Si en algún momento el auto-sync se vuelve molesto (commits espurios, falsos positivos, rate limiting), hay tres niveles de freno:

1. **Pausa temporal por UI:** Settings → Actions → Workflows → "Sync Roadmap" → Disable workflow. Reactivable con un click. Los issues no se pierden; cuando se reactiva el cron diario lo regenera.
2. **Pausa selectiva:** comentar los triggers en `.github/workflows/sync-roadmap.yml`. Por ejemplo, dejar solo `workflow_dispatch` y `schedule` (sin events de issue) si los triggers por evento están saturando.
3. **Apagado total:** borrar `.github/workflows/sync-roadmap.yml` y dejar `ROADMAP.md` editado a mano hasta nuevo aviso. El script sigue siendo invocable manualmente con `python scripts/generate_roadmap.py`.

Si se decide deprecar el sistema entero, generar un ADR 00XX `Superseded by` que explique qué lo reemplaza.

## References

- `scripts/generate_roadmap.py` — implementación del generador
- `.github/workflows/sync-roadmap.yml` — orchestrador
- `ROADMAP.md` — output renderizado, en raíz del repo
- [Project "SICA Roadmap"](https://github.com/users/aaronhuaynate66/projects/2) — vista kanban complementaria
- `STRATEGY.md` § 19 (equipo y hiring) — escala futura que valida tener este sistema en su lugar antes de que el equipo crezca
- [GitHub Docs: Workflow triggers](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows)
- [GitHub Docs: GITHUB_TOKEN does not trigger workflows](https://docs.github.com/en/actions/security-guides/automatic-token-authentication#using-the-github_token-in-a-workflow)

## Revisión

Esta decisión se revisa explícitamente en uno de estos triggers:

- El equipo supera 5 contributors activos y el modelo de Project + ROADMAP no escala.
- Movemos `STRATEGY.md` y `docs/roadmap.md` fuera del repo (improbable, pero si pasara, el roadmap operativo cambia de naturaleza).
- Implementamos una capa de billing o métricas de uso clínico que merezca un dashboard dedicado (post-R5).
- GitHub Issues deja de ser la fuente de verdad del trabajo operativo (ej. migración a Linear o Jira). En ese caso este ADR queda `Superseded`.

Hasta entonces, **Living Roadmap System auto-sincronizado desde GitHub Issues** es la elección.
