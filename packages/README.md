# packages/

Paquetes TypeScript compartidos entre apps. Cada subcarpeta es un paquete de workspace pnpm.

## Estado

Vacío. Los packages compartidos (`@sica/fhir-types`, `@sica/ui`, `@sica/eval-sdk`, etc.) aparecen cuando hay dos consumidores reales — no antes.

## Convenciones

- Una carpeta por package: `packages/<nombre>/`.
- Naming: `@sica/<nombre>` en `package.json`.
- No crear packages especulativamente. Solo cuando hay duplicación real entre apps o servicios.

Ver [ADR 0001](../docs/decisions/0001-monorepo-turborepo.md).
