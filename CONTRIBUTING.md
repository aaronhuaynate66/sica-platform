# Cómo contribuir a SICA

> Si entrás por primera vez al repo, leé también [`README.md`](README.md)
> y [`MASTER_PLAN.md`](MASTER_PLAN.md). Para el contexto estratégico
> completo: [`STRATEGY.md`](STRATEGY.md).

Este documento cubre las reglas operativas del repo (workflow, gates,
linting, deployment). Todo en español por convención del equipo.

---

## Workflow general

- **Branch:** trabajamos directo sobre `main` cuando la sesión es
  autónoma y el cambio cabe en un commit atómico. Para cambios largos
  o sensibles (>200 LOC, schema migrations, prompt cambios) abrir PR.
- **Conventional commits:** `feat:`, `fix:`, `chore:`, `docs:`,
  `test:`, `refactor:`, `perf:`. Scope opcional entre paréntesis:
  `feat(ci): …`. Mensajes en español.
- **Issues:** el `MASTER_PLAN.md` se regenera desde la actividad de
  GitHub Issues. Cerrar issues cuando el trabajo está hecho — el bot
  sincroniza el plan al siguiente push.

---

## Pre-commit hooks

Recomendado pero opcional. Replican un subset de lo que corre CI.

### Linux / Mac

```bash
./scripts/setup-pre-commit.sh
```

### Windows

```powershell
./scripts/setup-pre-commit.ps1
```

Hooks activos: `ruff check`, `ruff format --check`, verificaciones
genéricas (whitespace, YAML válido, archivos >1 MB, conflict markers,
llaves privadas sueltas). Ver `.pre-commit-config.yaml`.

---

## Lint y tests antes de commitear

Mínimo a verificar localmente:

```bash
# Python (cada servicio en services/ y evals/)
cd evals && ruff check . && pytest
cd services/clinical-extractor && ruff check . && pytest

# TypeScript / Next.js
pnpm lint && pnpm type-check
```

CI corre estos mismos checks (`.github/workflows/ci.yml`) y el
harness gate (`.github/workflows/harness-gate.yml`) — si no
los corrés localmente, los verás fallar tarde en el PR.

---

## Harness Gate

Cualquier PR que toque código del extractor
(`services/clinical-extractor/`), del harness (`evals/`) o del API
(`apps/api/`) dispara automáticamente el **harness gate**.

### Qué hace el gate

1. Instala `sica-evals` y `clinical-extractor` en un runner limpio.
2. Corre extracción real (Claude Sonnet 4.5) contra 3 casos
   sintéticos representativos:
   - `synthetic_case_01` — control normal, baseline canónico.
   - `synthetic_case_02_preeclampsia` — patología crítica con
     campos críticos múltiples.
   - `synthetic_case_06_anemia_severa` — edge case con valor
     crítico (Hb 7.2).
3. Compara métricas vs el baseline canónico
   (`evals/fixtures/baselines/claude_sonnet_4_5_synthetic_case_01.baseline.json`).
4. Bloquea el merge si alguna métrica viola threshold.
5. Postea (o edita) un comentario en el PR con la tabla de deltas.
6. Aplica/remueve el label `harness-failure` según el resultado.

### Thresholds activos

Ver [`.github/harness-thresholds.yaml`](.github/harness-thresholds.yaml).

| Métrica | Tipo | Tope |
|---|---|---|
| `factual_accuracy` | `relative_decline` | máx -3 pp vs baseline |
| `critical_omissions` | `absolute_max` | 5 total |
| `hallucination_count` | `absolute_max` | 0 (cero tolerancia) |
| `ece` (calibration error) | `absolute_max` | 0.15 |

### Cuándo bypassear el gate

Solo si tenés alta confianza de que el cambio **no afecta extracción**:

- Refactor puro sin cambio de lógica.
- Cambios en docs (`*.md`), tests del frontend, CI config no relacionada.
- Bumps de dependencias del frontend.

Aplicá el label `skip-harness-gate` al PR. **Documentá en el PR por
qué se bypassea** — auditamos esos PRs después.

### Cuándo actualizar el baseline

Si tu PR mejora intencionalmente las métricas (e.g. nuevo prompt,
fix de hallucination, schema enriquecido):

1. PR separado del cambio que mejora.
2. Label `baseline-update`.
3. Subí el nuevo `*.baseline.json` a `evals/fixtures/baselines/` y
   actualizá `config.baseline_path` en `harness-thresholds.yaml`
   si cambiaste el nombre del baseline canónico.
4. El PR queda flagged y requiere review humano explícito (no es
   un cambio que se hace solo).

> Lock blando: hasta `2026-09-01` el baseline NO se actualiza sin
> label explícito (ver `config.baseline_locked_until`).

### Costo

- Por corrida del gate: **~USD 0.10** (3 PDFs cortos × ~USD 0.035).
- Mensual con 20-30 PRs activos: **~USD 2-3**.
- Aceptable para R0/R1. Reevaluamos en R2 si la actividad crece.

---

## Setup inicial del CI (solo una vez, admin del repo)

El workflow `harness-gate.yml` requiere el secret `ANTHROPIC_API_KEY`
configurado en el repo.

### Pasos

1. Navegar a:
   ```
   https://github.com/aaronhuaynate66/sica-platform/settings/secrets/actions
   ```
2. Click **"New repository secret"**.
3. Name: `ANTHROPIC_API_KEY`.
4. Value: pegar API key de `console.anthropic.com`.
   - Generar una key dedicada para CI con scope mínimo.
   - Rotar cada 90 días.
5. Click **"Add secret"**.

### Verificar que funciona

1. Ir a la pestaña **Actions** del repo.
2. Workflow **"Harness Gate"** debe aparecer listado.
3. Disparar manualmente:
   - Click **"Run workflow"** (esquina superior derecha).
   - Branch: `main`.
   - (Opcional) Lista de casos custom.
   - Click **"Run workflow"**.
4. Esperar 2-3 minutos.
5. Job debe terminar con status verde y subir un artifact
   `harness-report-{run_id}`.

### Setup de labels canónicos (una vez)

```bash
# Linux / Mac
./scripts/setup-labels.sh

# Windows
./scripts/setup-labels.ps1
```

Idempotente — re-aplica sin riesgo. Crea / actualiza los labels
declarados en `.github/labels-init.yml`.

---

## ADRs (decisiones arquitectónicas)

Para decisiones que afectan arquitectura, dependencias o políticas
del producto, crear un ADR en `docs/decisions/` siguiendo el formato
de los existentes. Numerados secuencialmente.

El bot referencia automáticamente todos los ADRs en `MASTER_PLAN.md`.

---

## Reportar problemas o vulnerabilidades

- **Bugs / feature requests:** abrir issue en GitHub.
- **Vulnerabilidades de seguridad:** ver
  [`SECURITY.md`](SECURITY.md) — no abrir issue público.
