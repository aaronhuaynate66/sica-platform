# 0008. Prompt Registry con Versionado y Hash Determinístico

- **Status:** Accepted — 2026-05-26 — Fase 1 implementada
- **Date:** 2026-05-26
- **Deciders:** Aaron Huaynate (founder / CTO)
- **Tags:** prompts, observability, audit-trail, versionado, infra
- **Related:** [ADR 0004](0004-model-routing-policy.md) (model routing), [ADR 0005](0005-evaluation-methodology.md) (evaluation methodology), [ADR 0007](0007-langfuse-observability.md) (Langfuse observability — trace context lleva el hash del prompt)

## Context

El extractor clínico de SICA depende de un prompt versionado para cumplir tres restricciones de R0–R1:

1. **Auditoría regulatoria** (STRATEGY § 13). Dada una extracción específica corrida un día específico, debe ser posible reconstruir **el prompt exacto** que la produjo — bit por bit, sin ambigüedad. Esto importa porque el output del extractor entra en flujos clínicos asistivos y la trazabilidad es requisito de la Ley 29733 + DPIA.

2. **Reproducibilidad de evals**. Cuando el harness de evaluación reporta "factual_accuracy 0.92", esa métrica está ligada a una versión específica del prompt. Si el prompt cambia silenciosamente (typo arreglado, sinónimo movido, espacio borrado), la métrica histórica deja de ser comparable.

3. **Rollback rápido cuando un cambio regresiona**. Si un nuevo prompt baja la calidad, queremos poder revertir a la versión anterior **sin tocar código** — solo cambiando qué versión está activa en producción.

El estado pre-fase-1 era: el prompt vivía como **string literal multilínea** dentro de `services/clinical-extractor/src/clinical_extractor/prompts.py` (commit pre-registry). Esto fallaba las 3 restricciones:

- **No auditable**: cualquier edición del file cambiaba el prompt en runtime sin generar señal observable. Un commit `chore: fix typo en prompt` cambiaba la behavior del extractor sin que apareciera en métricas o traces.
- **Sin reproducibilidad**: el prompt no tenía hash propio; correlacionar una extracción del 22-may con "el prompt que estaba activo el 22-may" requería `git blame` manual.
- **Sin rollback**: solo había una versión a la vez. Volver a una versión anterior requería revertir el commit, romper compatibilidad con otros cambios, y redeploy.

Además, los siguientes 2 trimestres requieren capacidades que **no son viables sin versionado explícito**:

- **A/B testing de prompts** (R1.5+): correr 2 versiones en paralelo sobre subset de tráfico, comparar métricas, promover el ganador.
- **Routing por contexto** (R2+): elegir un prompt distinto según el tipo de documento (control normal vs urgencia) o el partner.

## Decision

**Fase 1 (este ADR, ya implementada — commits `6baa80d` + `f6e662b`)**: introducir un **package `prompts/`** con tres componentes:

### 1. Archivos `.md` por versión

Estructura:

```
services/clinical-extractor/src/clinical_extractor/prompts/
├── __init__.py          ← wrapper que preserva API legacy 100%
├── registry.py          ← API nueva (PromptVersion, get_prompt, ...)
└── versions/
    ├── __init__.py
    └── extract_obstetric_v1.md   ← contenido del prompt
```

Convención de naming: `{nombre_logico}_v{N}.md`. El "nombre lógico" (`extract_obstetric`) es estable; el `_vN` se incrementa al crear una nueva versión. **Nunca se edita un `.md` in-place** — eso es violación del contrato, detectable por el test `test_known_prompt_hash_is_stable` que ancla el hash exacto del v1 en CI.

### 2. Estructura interna del `.md`

Cada archivo contiene `## SYSTEM` y `## USER_TEMPLATE` como delimitadores. Los dos prompts (system + user_template) son **inseparables semánticamente** — un cambio sutil en user_template afecta cómo el modelo interpreta el system. Mantener ambos en el mismo file preserva atomicidad de diffs y simplifica la auditoría ("un commit = una versión").

El header `# {name}_v{N}` arriba es comentario humano; el parser ignora todo lo previo al primer marcador.

### 3. API del registry (`registry.py`)

```python
@dataclass(frozen=True)
class PromptVersion:
    name: str
    version: int
    system: str
    user_template: str
    hash: str           # SHA256 del raw_content completo
    raw_content: str    # contenido bruto del file
    file_path: Path

def get_prompt(name: str, version: int) -> PromptVersion: ...
def get_active_prompt(name: str, version_override: int | None = None) -> PromptVersion: ...
def list_versions(name: str) -> list[int]: ...
def latest_version(name: str) -> int: ...
def clear_cache() -> None: ...
```

`@functools.cache` sobre `_load_prompt(name, version)` garantiza un solo read por proceso. `clear_cache()` para tests.

`get_active_prompt(name, version_override=None)`:

- `version_override` provisto → carga esa versión exacta.
- `None` → usa `latest_version(name)`.

Fase 2 enchufará routing A/B en este punto sin tocar callers — el extractor sigue llamando `get_active_prompt("extract_obstetric")` y el registry decide.

### 4. Compatibilidad legacy 100%

`prompts/__init__.py` reexpone la API anterior (`VersionedPrompt` NamedTuple, `PROMPT_V0_1_0`, `PROMPT_REGISTRY: dict[str, VersionedPrompt]`, `ACTIVE_PROMPT_VERSION = "0.1.0"`, `get_active_prompt()` sin args, `get_prompt(version: str)`) construyéndola **lazily al import** sobre el registry. El extractor (`anthropic_provider.py`) sigue haciendo `request.prompt.user_template.format(document_text=...)` sin saber que el prompt viene de un `.md`.

Esta decisión (Opción A del plan original) tiene zero-impact en código consumidor. Las opciones B (vaciar prompts.py + actualizar imports) y C (función get_system_prompt() dinámica) quedan reservadas para Fase 2 cuando A/B testing requiera dinamismo no-cacheable.

### 5. Versión activa actual

Al 2026-05-26:

- `extract_obstetric_v1.md` — único archivo en `versions/`.
- Hash: `9241ec0d...` (test `test_known_prompt_hash_is_stable` lo ancla).
- Contenido: idéntico carácter-por-carácter al `_SYSTEM_V0_1_0` + `_USER_TEMPLATE_V0_1_0` legacy. Verificado pre-commit con `exec()` del file original.

## Consequences

### Positivas

- **Cualquier cambio al prompt requiere crear `_vN+1.md`** y no edición silenciosa. Los `.md` nuevos producen hash distinto automáticamente; los reviewers ven el archivo nuevo en el PR.
- **Hash en logs + traces correlaciona observability con versión exacta**. Cada vez que el extractor arranca, loggea `Prompt activo: extract_obstetric_v1 (hash=9241ec0d)`. Cuando Langfuse muestre una trace, podemos cruzar con git el commit donde apareció ese hash.
- **Tests del prompt mismo previenen regresiones** (`test_hash_is_deterministic`, `test_known_prompt_hash_is_stable`, `test_legacy_content_matches_registry`). Si el parser cambia o el .md se edita, los tests rompen en CI antes del merge.
- **Listo para A/B testing (Fase 2)**: solo agregar routing en `get_active_prompt`. La firma `(name, version_override=None)` puede extenderse a `(name, strategy="ab", split=0.5)` sin romper callers.
- **Listo para rollback rápido**: setear `version_override` en producción vía env var `PROMPT_OVERRIDE_VERSION` (Fase 2) es 5 líneas de código sobre el registry actual.
- **Migración de prompts.py es transparente**: extractor sin cambios, 111/111 tests pre-existentes pasan.

### Negativas

- **Más archivos en el repo**: 1 por versión. Aceptable hasta ~50 versiones (escala R2-R3). A partir de ahí: o bien organizar en subdirectorios por release (`versions/r0/`, `versions/r1/`), o bien migrar a DB externa (ver Alternativa D).
- **Convención de naming debe respetarse**: `_vN.md` con N entero. El parser de `_parse_filename` rechaza formatos distintos, así que un archivo mal nombrado simplemente no se carga (silencioso). Mitigación: test `test_list_versions_returns_sorted` lista versiones disponibles y falla si se esperaban otras.
- **Cambios menores (typo, espacio) requieren bump de versión**: trade-off aceptado conscientemente. La regla "un cambio = una versión" hace el sistema más ruidoso pero más auditable. Cuando un cambio sea trivial, el commit message lo explica (`prompts(extract_obstetric_v2): fix typo en regla 4 — funcionalmente identico, hash cambia por whitespace`).
- **Atomicidad técnica B1+B2**: la conversión de `prompts.py` (módulo) a `prompts/` (package) NO es separable en commits porque Python no permite coexistir ambos con el mismo nombre. El commit `6baa80d` necesariamente borra el `.py` y crea el package en una sola operación.

### Neutras

- **Fase 1 NO incluye A/B routing automático** (Fase 2).
- **Fase 1 NO incluye rollback automático en regresión** (Fase 3).
- **Storage en repo, no en DB externa**. Cabe holgadamente en R0/R1; revisar en R2 si: a) el repo se vuelve >500 MB por archivos `.md`, b) necesitamos editar prompts sin redeploy (DB-backed), c) un partner exige multi-tenant con prompts por cliente.

## Alternatives considered

### Alternativa A: carpetas por versión

`versions/v1/extract_obstetric.md`, `versions/v2/extract_obstetric.md`.

**Por qué no**: para 1 archivo por carpeta, la estructura suma profundidad sin valor. Cuando una versión tenga múltiples sub-archivos (ej. `system.md` + `user.md` + `examples.md` separados), reconsiderar.

### Alternativa B: variables en código Python

```python
EXTRACT_OBSTETRIC_V1 = """..."""
EXTRACT_OBSTETRIC_V2 = """..."""
```

**Por qué no**:
- Fuerza recompilación + redeploy para cualquier cambio de prompt.
- Impide A/B testing sin redeploy.
- Strings multilínea en Python son frágiles para diffs (indentation, escape).
- Es exactamente el patrón pre-fase-1 que estábamos resolviendo.

### Alternativa C: solo git history (sin versionado explícito)

**Por qué no**: no permite servir **múltiples versiones simultáneamente** (A/B). Y la trazabilidad "qué prompt corrió en qué deploy" requiere reconstruir manualmente del git log.

### Alternativa D: DB externa (e.g. Langfuse Prompts, LaunchDarkly)

**Por qué no en R0/R1**:
- Overhead de mantener otro servicio.
- Latencia adicional en cada extracción (HTTP roundtrip al cargar prompt — o cachear localmente, lo cual nos lleva al patrón actual de todos modos).
- Las soluciones gestionadas (Langfuse Prompts) cobran por uso.
- En R0 tenemos exactamente 1 prompt activo; un DB para 1 string es over-engineering.

**Cuándo reconsiderar**: en R2+ si: a) >10 prompts simultáneos en uso, b) necesidad de cambios de prompt sin commit/redeploy, c) prompts diferenciados por tenant.

### Alternativa E: frontmatter YAML obligatorio

```yaml
---
name: extract_obstetric
version: 1
author: Aaron Huaynate
created: 2026-05-26
description: Prompt inicial para historia obstétrica peruana
---
## SYSTEM
...
```

**Por qué no en Fase 1**: zero-feature en este momento (el filename ya contiene name + version; el git history ya contiene author + created date). **Reservado para Fase 2** cuando A/B testing necesite metadata declarativa (target_population, expected_metrics, etc.).

## Plan Fase 2 (R1.5+)

Disparadores para arrancar Fase 2:

- Se acerca el primer cambio de prompt con riesgo de regresión (e.g. ajuste para reducir hallucinations en `lab_results`).
- El equipo crece a ≥2 personas tocando prompts.

Capacidades a agregar:

- **Routing A/B**: `get_active_prompt("extract_obstetric", strategy="ab", split=0.5)` o por hash del request_id. Define qué % del tráfico cae en cada versión.
- **Métricas por versión en Langfuse**: cada generation en Langfuse llevará en metadata `prompt_version_string` + `prompt_hash`. Dashboard agrupado por hash da `factual_accuracy_by_prompt_version`.
- **Comparator offline**: script que toma 2 versiones y un dataset, corre el extractor sobre el dataset con ambas versiones, computa delta de métricas. Output al ADR de la promoción.

## Plan Fase 3 (R2+)

Disparadores:

- Producción tiene ≥3 versiones diferentes en uso para distintos casos.
- Hay tráfico suficiente para detectar regresiones estadísticamente.

Capacidades:

- **Rollback automático**: si factual_accuracy de la versión "active" cae más de X pp en N minutos, el routing revierte automáticamente a la última versión estable.
- **Promoción manual**: después de validación, un PR explícito mueve una versión candidata a "default". El "default" se setea en un archivo `versions/active.toml` o similar.
- **Frontmatter YAML obligatorio** con `name, version, author, created, description, target_population, expected_metrics`. Los reviewers pueden auditar el contrato sin leer el prompt.

## References

- **Commits Fase 1**:
  - `6baa80d` — `feat(prompts): add versioned prompt registry with deterministic hashing` (registry + package + tests, conversión atómica de prompts.py)
  - `f6e662b` — `refactor(prompts): load active prompt from registry transparently (no behavior change)` (smoke test E2E + snapshot fixture)
  - (commit del ADR) — `docs(adr): document prompt registry decisions (ADR-0008)`

- **Archivos clave**:
  - `services/clinical-extractor/src/clinical_extractor/prompts/registry.py` — implementación.
  - `services/clinical-extractor/src/clinical_extractor/prompts/versions/extract_obstetric_v1.md` — prompt v1 (hash `9241ec0d`).
  - `services/clinical-extractor/tests/test_prompt_registry.py` — 26 tests de invariantes.
  - `evals/fixtures/prompts/smoke_v1_synthetic_case_01.json` — snapshot del smoke test que verificó zero-regression.

- **ADRs relacionados**:
  - ADR 0004 (model routing): el routing de modelos y el de prompts son ortogonales — un modelo puede correrse con N versiones de prompt, y un prompt con M modelos. Ambos se loggean a Langfuse.
  - ADR 0005 (evaluation methodology): el harness gate ya está listo para correr con un prompt específico cuando agreguemos `--prompt-version` al CLI del harness (Fase 2).
  - ADR 0007 (Langfuse observability): el `generation.metadata` ya tiene un campo `extractor_version`; cuando Fase 2 lo enriquezca con `prompt_version_string` + `prompt_hash`, el dashboard de Langfuse podrá filtrar / agrupar por versión de prompt.

## Revisión

Esta decisión se revisa explícitamente en uno de estos triggers:

- **Aparece el primer prompt v2** — validar que la convención y el parser escalan.
- **Se requiere A/B testing** (R1.5) — disparar Fase 2.
- **Se requiere rollback automático** (R2) — disparar Fase 3.
- **El repo crece >100 archivos en `versions/`** — evaluar migración a DB.
- **Cambia el contrato de Langfuse generations** — actualizar el snapshot del smoke fixture.

Hasta entonces, **Prompt Registry Fase 1 con `.md` versionados y hash SHA256 determinístico** es la configuración operativa.
