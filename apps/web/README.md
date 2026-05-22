# @sica/web

Primera UI de SICA. Next.js 15 App Router con cuatro vistas conectadas que demuestran las capacidades core del producto sobre datos sintéticos.

> **Status:** Demo interna. **No es producto.** **No es paciente real.**
> Toda la data es sintética y está marcada como tal en cada vista.

## Qué es

Cuatro vistas que demuestran la propuesta de valor de SICA sin tocar dato clínico real:

| Ruta | Vista | Demuestra |
|------|-------|-----------|
| `/` | **Upload & Extract** | PDF → JSON estructurado con confidence + evidencia trazable |
| `/timeline` | **Timeline gestacional** | Reconstrucción longitudinal del embarazo con eventos clínicos |
| `/dashboard` | **Dashboard de clínica** | Vista operacional densa (Bloomberg-style) sobre cohort sintético |
| `/physician` | **Panel del médico** | Modo asistivo Palantir-style: tareas, contexto, sugerencias con confidence |

Inspiración explícita: Linear (velocidad), Notion (estructura), Bloomberg Terminal (densidad), Palantir Gotham (capa cognitiva).

## Cómo correrla

Desde la raíz del monorepo:

```bash
pnpm install                          # instala todas las deps del workspace
pnpm --filter @sica/web dev           # arranca dev server en http://localhost:3000
```

Comandos útiles:

```bash
pnpm --filter @sica/web build         # build de producción
pnpm --filter @sica/web type-check    # tsc --noEmit
pnpm --filter @sica/web lint          # next lint
```

## Stack

- **Next.js 15.5** (App Router, RSC, static rendering)
- **TypeScript 5** (strict)
- **Tailwind CSS 4** (sin `tailwind.config.*`; configuración inline en `app/globals.css`)
- **shadcn/ui** (preset `base-nova`, sobre Base UI no Radix)
- **lucide-react** para íconos
- **next-themes** para toggle dark/light (default dark)

## Datos

- **Fixture canónico (R0):** `apps/web/lib/fixtures/synthetic_case_01.json` — copia de
  `evals/fixtures/synthetic_case_01.expected.json`. Sincronización manual hasta que exista `apps/api`.
- **PDF de demo:** `apps/web/public/synthetic_case_01.pdf` — copia de
  `services/clinical-extractor/data/synthetic_case_01.pdf`. Excepción explícita en `.gitignore` raíz.
- **Pacientes ficticios:** `apps/web/lib/mock-data/patients.ts` (10 entradas inventadas para Dashboard).
- **Tareas/sugerencias del médico:** `apps/web/lib/mock-data/physician.ts` (7 tareas + 5 sugerencias).
- **Eventos timeline:** `apps/web/lib/mock-data/timeline.ts` (10 eventos sobre el caso 01).

**Ningún dato es real.** Toda interacción con paciente real está fuera de scope hasta:
1. Validación clínica formal por equipo médico,
2. Inscripción del banco de datos personales ante la ANPD (Ley 29733),
3. Consulta con DIGEMID para clasificación de software asistivo,
4. Aprobación regulatoria explícita.

Ver `STRATEGY.md` § 14 y los issues `#1`, `#2`, `#3` en el repo.

## Estructura

```
apps/web/
├── app/
│   ├── layout.tsx              ← layout global + nav + disclaimer + theme
│   ├── page.tsx                ← Vista 1: Upload & Extract
│   ├── timeline/page.tsx       ← Vista 2: Timeline gestacional
│   ├── dashboard/page.tsx      ← Vista 3: Dashboard de clínica
│   ├── physician/page.tsx     ← Vista 4: Panel del médico
│   └── globals.css             ← Tailwind v4 inline + theme vars
├── components/
│   ├── ui/                     ← shadcn/ui auto-generated
│   ├── site/                   ← nav, theme provider, disclaimer
│   └── clinical/               ← confidence bar, evidence sheet
├── lib/
│   ├── fixtures/               ← copia del JSON canónico
│   ├── types/                  ← tipos TS que mirror Pydantic schemas
│   ├── mock-data/              ← pacientes, timeline, tareas (DEMO)
│   └── utils.ts                ← cn() helper
└── public/synthetic_case_01.pdf ← PDF demo (excepción gitignore)
```

## Modo demo vs modo live

La vista `/` (Upload & Extract) opera en dos modos según `NEXT_PUBLIC_API_MODE`:

| Modo | Comportamiento |
|---|---|
| `demo` (default) | Botón "Cargar PDF de ejemplo" usa el fixture sintético. "Subir PDF propio" muestra un mensaje pidiendo acceso. Cero llamadas al backend. |
| `live` | La UI verifica `/health` del backend al montar. Si responde, ofrece extracción real vía `POST /extract`. Si no responde, cae automáticamente a comportamiento `demo` con badge en amarillo. |

### Variables de entorno

Copiar `.env.example` a `.env.local` (gitignored) para dev:

```bash
cp .env.example .env.local
```

| Variable | Default | Descripción |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Base URL del backend `sica-api`. |
| `NEXT_PUBLIC_API_MODE` | `demo` | `demo` o `live`. Live habilita "Subir PDF propio". |

En Vercel, configurar estas vars en el dashboard del proyecto (Production + Preview). Ver `apps/web/VERCEL.md`.

### Cliente HTTP

El cliente vive en `lib/api/`:

- `client.ts` — `getHealth()`, `getModels()`, `extractFromPdf(file)` con timeout configurable y clases de error tipadas (`ApiError`, `ApiTimeoutError`, `ApiUnavailableError`).
- `types.ts` — interfaces TS que espejan `apps/api/src/sica_api/schemas.py`.
- `mode-detector.ts` — `getConfiguredMode()`, `isApiAvailable()` con cache de 30s, `resolveEffectiveMode()`.

Tests: `pnpm --filter @sica/web test`.

## Próximos pasos

| Cuando | Qué |
|--------|-----|
| Exista auth | Quitar disclaimer público, agregar login. |
| Pase gate R1 (>70% resúmenes útiles) | Quitar fallback a fixture estático; live mode obligatorio. |
| R2 (Shadow Mode) | Vista 4 conecta a HIS via launch button contextual. |

## Notas técnicas

- **PNPM 11 `allowBuilds`:** los install scripts de `sharp`, `unrs-resolver` y `msw` se gestionan vía `pnpm-workspace.yaml`. Sin esa config, `pnpm install` aborta. Ver `pnpm-workspace.yaml`.
- **Base UI vs Radix:** shadcn/ui en su versión actual (`base-nova` preset) usa `@base-ui/react`. La API es similar pero usa `render` prop en lugar de `asChild`. Si copy-pasteás snippets viejos de shadcn, traducí.
- **Theme dark default:** configurado en `next-themes` con `defaultTheme="dark"` y `enableSystem={false}`. Toggle visible en el nav.
- **Disclaimer:** banner sticky en bottom con "Datos sintéticos · No es paciente real · No clínicamente validado". No se puede ocultar — es deliberado para esta fase.
