<!--
Plantilla obligatoria de PR de SICA.
Borra las secciones que no aplican, pero NUNCA borres la sección "Riesgo clínico/regulatorio".
-->

## Qué cambia

<!-- Resumen en 1-3 frases. ¿Qué hace este PR? -->

## Por qué

<!--
Motivación. Idealmente links al issue / ADR / sección de STRATEGY.md que lo origina.
Si el PR cambia comportamiento clínico o de modelo, explica el "por qué ahora".
-->

## Cómo probarlo

<!--
Pasos exactos para reproducir el cambio localmente o en preview.
Si toca el extractor o eval suite, incluir el comando exacto (ej: pnpm -F clinical-extractor test, o pytest -k <name>).
-->

```bash
# comandos aquí
```

## Checklist obligatorio

- [ ] Tests pasan (`pnpm test` y/o `pytest` según corresponda)
- [ ] Lint pasa (`pnpm lint`, `ruff check`)
- [ ] Type-check pasa (`pnpm type-check`, `mypy`)
- [ ] Documentación actualizada si el PR introduce comportamiento nuevo
- [ ] **Sin secretos en el diff** — `.env`, API keys, tokens, credenciales
- [ ] **Sin PHI en el diff** — datos reales de pacientes, historias clínicas, identificadores
- [ ] Si el PR toca prompts o modelos: corrida de eval regression adjunta o explicada
- [ ] Si el PR toca esquemas FHIR / Pydantic: ADR o nota en el PR justificando el cambio

## Links

<!-- Issues / ADRs / docs relacionados -->

- Closes #
- Relacionado con #
- ADR:

## Riesgo clínico / regulatorio

**¿Este PR afecta seguridad clínica, manejo de PHI, o postura regulatoria?**

- [ ] **No** — cambio puramente técnico (infra, refactor, lint, docs internos, tooling).
- [ ] **Sí** — explicar abajo:

<!--
Si marcaste "Sí", explica:
- Qué cambia en términos clínicos o regulatorios.
- Qué validaciones se corrieron antes de mergear.
- Quién (médico / asesor regulatorio) revisó.
- Si el PR debe esperar firma externa antes de merge a main.
-->

## Notas de revisor

<!-- Cualquier cosa que el revisor deba saber: edge cases, decisiones provisionales, deuda técnica aceptada. -->
