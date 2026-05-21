# Architecture Decision Records (ADRs)

Este directorio contiene los ADRs de SICA. Un ADR es un documento corto que registra **una decisión arquitectónica significativa**, el contexto en que se tomó, las alternativas consideradas, y las consecuencias aceptadas.

## Por qué ADRs

> "We didn't choose this because it was the best option. We chose it because we needed to choose, and this was the least wrong at the time."

Sin ADRs, las decisiones se desvanecen en chats, PRs y en la cabeza de quien las tomó. Seis meses después nadie recuerda **por qué** algo se eligió, y el equipo nuevo asume que fue accidente o ignorancia — entonces lo revierte sin entender el costo.

Un ADR responde tres preguntas que el código no responde:

1. **¿Qué se decidió?**
2. **¿Por qué se decidió eso y no otra cosa?** (las alternativas son la parte más valiosa)
3. **¿Qué se acepta como costo?**

## Cuándo escribir un ADR

Escribe un ADR si la decisión:

- **Es difícil de revertir.** Cambia la forma de la base de código o cómo se opera el sistema.
- **Tiene alternativas serias.** Si solo había un camino, no es decisión, es ejecución.
- **Afecta a futuros miembros del equipo.** Si alguien que entra al proyecto va a preguntar "¿por qué así?", merece ADR.
- **Toca seguridad clínica, regulación, o manejo de PHI.** Estas decisiones tienen consecuencias legales y deben estar trazables.

No escribas ADR para: elección de variable name, decisión local de un módulo, refactor sin cambio de invariante.

## Formato

Usamos [MADR](https://adr.github.io/madr/) (Markdown Architecture Decision Records). Plantilla mínima:

```markdown
# {N}. {Título breve en imperativo}

- **Status:** Proposed | Accepted | Deprecated | Superseded by ADR-XXXX
- **Date:** YYYY-MM-DD
- **Deciders:** {nombres o roles}

## Context

{Por qué necesitamos decidir. Qué problema o restricción genera esta decisión ahora.}

## Decision

{Lo que decidimos hacer, en una frase, y luego el detalle.}

## Consequences

### Positive
- ...

### Negative
- ...

## Alternatives considered

### Alternativa A
{Qué era, por qué la descartamos.}

### Alternativa B
...

## References

{Links a discusiones, papers, repos de referencia.}
```

## Numeración

- ADRs van numerados secuencialmente desde `0001`.
- El número **nunca se reusa**, incluso si un ADR es deprecado.
- Archivo: `NNNN-titulo-en-kebab-case.md` — ejemplo: `0001-monorepo-turborepo.md`.

## Ciclo de vida

| Status | Significado |
|---|---|
| `Proposed` | Borrador en discusión. PR abierto. |
| `Accepted` | Decisión vigente. Mergeada. |
| `Deprecated` | Ya no aplica, pero no fue reemplazada por otra. Se documenta por qué se abandonó. |
| `Superseded by ADR-XXXX` | Una ADR posterior la reemplaza. El ADR original se mantiene como historia. |

**Nunca se borra un ADR.** Si la decisión cambió, se crea un ADR nuevo que la sobreescribe y el viejo cambia a `Superseded by ADR-XXXX`.

## Índice

| # | Título | Status | Fecha |
|---|---|---|---|
| [0001](0001-monorepo-turborepo.md) | Monorepo en sica-platform con Turborepo + pnpm | Accepted | 2026-05-20 |
| [0002](0002-living-roadmap-system.md) | Living Roadmap System: MASTER_PLAN.md auto-sincronizado desde issues | Accepted | 2026-05-21 |
