# GitHub Workflows

Workflows de CI/CD del monorepo SICA. Cada archivo en este directorio se ejecuta como un pipeline de GitHub Actions.

## Workflows actuales

| Workflow | Archivo | Triggers | Qué hace |
|---|---|---|---|
| **CI** | [`ci.yml`](ci.yml) | `pull_request` y `push` a `main` | Lint + type-check de paquetes Node/TS y servicios Python. Skip seguro si no hay nada que linter aún. |

## Principios

1. **Early-exit seguro.** En R0 el monorepo todavía está casi vacío. Los workflows detectan si hay algo que ejecutar (paquetes Node, servicios Python) y salen con éxito si no lo hay. Esto permite que PRs de docs / config no bloqueen merge por workflows que no aplican.
2. **Cancela corridas obsoletas.** `concurrency.cancel-in-progress: true` para no quemar minutos en commits que ya fueron superados.
3. **Permisos mínimos.** `permissions: contents: read` por default. Si un workflow necesita más, se declara explícitamente en ese job.
4. **Pin de versiones críticas.** Actions oficiales se referencian por major (`@v4`); pnpm se pinea a la versión exacta del `packageManager` del `package.json` raíz.

## Cómo agregar un workflow nuevo

1. Crear el archivo en `.github/workflows/<nombre>.yml`.
2. Agregarlo a la tabla de arriba.
3. Si el workflow consume secretos (`ANTHROPIC_API_KEY`, `LANGFUSE_*`, etc.), agregarlos en Settings → Secrets and variables → Actions del repo, y referenciarlos con `secrets.<NOMBRE>`. **Nunca** hardcodear secretos en el YAML.
4. Documentar en este README qué hace y cuándo se dispara.

## Workflows planeados (no implementados todavía)

| Workflow | Cuándo se necesita | Propósito |
|---|---|---|
| `eval-regression.yml` | R0 mid — cuando exista la primera suite de eval | Corre `evals/harness` sobre el fixture set en cada PR que toca prompts o modelos. Bloquea merge si métricas clave degradan. |
| `release.yml` | R1 | Builds + tag + changelog automatizado cuando se mergea a `main`. |
| `security-scan.yml` | R1 | Snyk / Dependabot / Trivy sobre dependencies y contenedores. |
| `e2e.yml` | R2 | Playwright contra preview deploy cuando hay UI clínica embebida. |
