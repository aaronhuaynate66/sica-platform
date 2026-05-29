# 0011. Stack del frontend SICA (Next.js + Supabase + Vercel)

- **Status:** Accepted — 2026-05-28
- **Date:** 2026-05-28
- **Deciders:** Aaron Huaynate (founder / CTO)
- **Tags:** frontend, supabase, vercel, auth, storage, architecture
- **Related:** [ADR 0001](0001-monorepo-turborepo.md) (monorepo), [ADR 0003](0003-security-and-phi-policy.md) (PHI), [ADR 0009](0009-phi-redaction-in-tracing.md) (PHI redaction)

## Context

Para R1 SICA necesita una UI de médico colaborador que permita:

- Autenticarse de forma confiable y sin password compartido.
- Subir PDFs de historias clínicas y persistir el `ObstetricSummary` que retorna `sica-api`.
- Listar pacientes y sus controles longitudinales.
- Comparar dos controles del mismo paciente.

La app debe estar en producción en `sica-web.vercel.app` esta semana, sobre un partner aún no firmado, con presupuesto operativo cercano a cero. **Decisiones reversibles, no compromisos arquitectónicos a 18 meses.**

## Decision

Stack:

| Capa | Elección | Por qué |
|---|---|---|
| Framework | **Next.js 15 (App Router) + TypeScript + Tailwind v4 + shadcn/ui** | Ya existía en `apps/web`. Server Components encajan con la necesidad de renderizar listas pre-autenticadas |
| Auth | **Supabase Auth — magic link (email OTP)** | Sin password compartido, sin necesidad de identity provider externo, soporta SSR vía `@supabase/ssr` |
| DB | **Supabase Postgres + RLS** | Una sola política `auth.uid() = user_id` aísla pacientes por médico. Sin server custom para esta fase |
| Storage | **Supabase Storage (bucket privado `pdfs`)** | Path convention `{user_id}/{paciente_id}/{control_id}.pdf` + RLS sobre `storage.objects` |
| Deploy | **Vercel** (proyecto `sica-web`) | Auto-deploy desde `main`. Env vars vía UI o `vercel env` |
| Backend AI | **`sica-api` en Render** (sin cambios) | Llamado desde server actions de Next; recibe PDF multipart y devuelve `ObstetricSummary` |

### Modelo de datos

Dos tablas en `public`:

- `pacientes` — `nombre_completo`, `dni`, `hc_id`, `fecha_nacimiento`. Datos completos (no redactados) porque el médico que los registró debe verlos completos (ADR 0009 § "El médico colaborador procesará...": los datos viven completos en memoria del extractor y bases controladas; sólo Langfuse Cloud recibe payload redactado).
- `controles` — `pdf_filename`, `pdf_storage_path`, `semanas_gestacion`, `fecha_control`, `resumen_json` (JSONB con el `ObstetricSummary` completo), más metadata operacional (`extractor_version`, `provider_id`, `cost_usd`, `latency_ms`, `trace_id`).

`resumen_json` como JSONB: el schema del extractor (`schemas.py`) es la única fuente de verdad. Modelar columna-por-campo duplicaría el contrato y rompería al primer cambio. JSONB conserva flexibilidad y permite indexar campos específicos si surge necesidad.

### Por qué Supabase y no alternativas

- **vs Firebase/Auth0 + Postgres separado**: una sola integración, una sola UI de admin, RLS estándar en SQL.
- **vs auth.js + Postgres custom**: requiere mantener server de DB + email provider + tabla de usuarios + sesión. Supabase entrega todo eso preempaquetado para R1.
- **vs Clerk + Postgres**: Clerk es mejor producto pero +USD ~25/mes por encima del Free tier de Supabase, sin valor diferencial en R1.
- **vs Convex/Neon + Auth.js**: equivalente técnicamente pero múltiples vendors. Supabase reduce la superficie de ops a un dashboard.

### Por qué magic link (sin password)

- **Wedge clínico es <10 médicos en R1**: emails confiables, no es público.
- **Sin password storage** simplifica compliance preliminar (Ley 29733 no requiere password storage si no hay password).
- **UX clínica**: el médico no necesita recordar otra contraseña.

### PHI y residencia de datos

Supabase Postgres se aprovisiona en `sa-east-1 (São Paulo)`. **Esto NO es residencia peruana** pero es la región LatAm más cercana disponible en el Free tier. Los datos clínicos viven completos en esa base porque:

- El médico que los registró tiene derecho a verlos completos (es su paciente).
- La redaction PHI de ADR 0009 aplica al envío externo (Langfuse Cloud US), no al storage operacional propio.

`[TODO crítico R2+]`: validar con asesor regulatorio si `sa-east-1` cumple Ley 29733 vía consentimiento informado del paciente que autoriza tratamiento. Hasta entonces, **solo usar con pacientes que firmaron consentimiento explícito**.

### Aislamiento por médico (RLS)

Una sola política por tabla: `auth.uid() = user_id`. Cada médico ve solo sus pacientes y controles. El `service_role` key (no expuesto al frontend) puede leer todo — uso restringido a server jobs auditados.

## Consequences

### Positivas

- **Tiempo a producción <8 horas**: stack maduro, sin custom infra.
- **Costo R1: USD 0** (Free tier Supabase + Vercel Hobby + Render free).
- **Una sola DB compartida** entre auth y app data — sin join cross-service.
- **Storage versionable**: los PDFs originales quedan en el bucket privado, recuperables vía signed URL temporal.
- **Reversible**: migrar a Postgres self-hosted + auth.js solo requiere export del schema y los datos. Supabase Auth usa JWT estándar.

### Negativas

- **Vendor lock-in operativo**: dashboard, RLS dialect propio (`auth.uid()`), Storage API propietaria. Mitigado por el hecho de que todo es SQL estándar + S3-compatible.
- **Region `sa-east-1` no es Perú**: residencia incompleta hasta validación regulatoria (ver TODO arriba).
- **Free tier tiene límites**: 500 MB DB, 1 GB storage, 50k MAU. En R1 con <10 médicos es holgado; revisar al pasar 100.
- **Sin self-hosting trivial**: Supabase OSS existe pero requiere ops dedicado. Diferimos a R2+.

### Neutras

- **Las dependencias de Next/React/Tailwind no cambian**: el proyecto ya estaba en Next 15 + Tailwind v4.
- **MCP de Supabase no estuvo disponible** en la sesión de bootstrap: el proyecto se crea manualmente vía UI siguiendo `supabase/README.md`. Cuando se conecte el MCP, las migraciones futuras pasarán por `supabase db push`.

## Alternativas consideradas

### Alternativa A: Auth.js + Postgres en Neon (DESCARTADO en R1)

Forma: NextAuth con email provider Resend + Postgres en Neon serverless.

Por qué no: tres vendors, tres dashboards, lógica de sesión custom. No aporta nada sobre Supabase en R1.

### Alternativa B: Firebase Auth + Firestore (DESCARTADO)

Por qué no: Firestore es NoSQL — pierde joins y SQL estándar. RLS Firebase es más limitada. Migración futura más costosa.

### Alternativa C: Clerk + Supabase (CONSIDERADO, descartado para R1)

Forma: Clerk para auth (mejor UX y MFA), Supabase para DB.

Por qué no: doble vendor de auth/sesión, integración non-trivial entre JWTs. Reconsiderar en R2+ si el MFA se vuelve requisito.

## Implementación R1 (esta sesión)

- `supabase/migrations/0001_initial_schema.sql` — tablas, índices, trigger, RLS, storage bucket + policies.
- `apps/web/.env.example` — placeholders Supabase.
- `apps/web/src/lib/supabase/{client,server}.ts` — clientes browser y SSR.
- `apps/web/src/middleware.ts` — refresh de sesión + redirección de rutas protegidas `/app/*`.
- `apps/web/src/app/login/` — magic link UI.
- `apps/web/src/app/auth/callback/route.ts` — exchange code for session.
- `apps/web/src/app/app/` — layout autenticado + rutas protegidas.
- `apps/web/src/lib/queries/` — helpers tipados para `pacientes` y `controles`.

## Revisión

Triggers de revisión obligatorios:

- **Free tier Supabase agotado** → migrar a Pro o decidir self-host.
- **Cliente clínico exige residencia Perú** → evaluar Supabase Pro con custom region, o self-host on-prem.
- **MFA mandatorio para roles administrativos** → reconsiderar Clerk.
- **R3+ multi-tenant cross-clínica** → repensar RLS scope (probable: agregar `clinica_id` y composite policy).
- **MCP de Supabase conectado** → migrar gestión de schema a `supabase db push` y eliminar el bootstrap manual.

## Referencias

- STRATEGY § 11.3 — stack recomendado (Next.js + Supabase).
- ADR 0001 — monorepo.
- ADR 0003 — PHI policy.
- ADR 0009 — PHI redaction antes de Langfuse Cloud.
- `supabase/README.md` — bootstrap manual del proyecto.
