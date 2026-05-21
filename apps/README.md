# apps/

Aplicaciones Next.js de SICA. Cada subcarpeta es un paquete de workspace pnpm independiente.

## Estado

Vacío. Las apps de Fase 2 (panel clínico alpha, harness web de evaluación) se crean a partir de R1.

## Convenciones

- Una carpeta por app: `apps/<nombre>/`.
- Cada app declara su `package.json` con `name: "@sica/<nombre>"`.
- Frontends viven aquí; servicios Python viven en `services/`; código compartido TS vive en `packages/`.

Ver [ADR 0001](../docs/decisions/0001-monorepo-turborepo.md) para la decisión arquitectónica.
