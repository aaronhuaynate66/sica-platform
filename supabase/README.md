# Supabase — SICA

Esquema, migraciones y guía de bootstrap del proyecto Supabase de SICA.

## Bootstrap manual (R1, 2026-05-28)

El MCP de Supabase no está conectado a esta sesión, así que el proyecto se crea
por la UI. Los pasos siguientes son la única ruta soportada hasta que el MCP
se conecte (ver [`docs/decisions/0011-frontend-stack.md`](../docs/decisions/0011-frontend-stack.md)).

1. **Crear proyecto**
   - URL: <https://supabase.com/dashboard/projects>
   - Name: `sica-platform`
   - Region: `South America (São Paulo) — sa-east-1`
   - Plan: Free
   - DB password: generar uno fuerte y guardarlo en password manager.

2. **Capturar credenciales** (Project Settings → API)
   - `Project URL` → `NEXT_PUBLIC_SUPABASE_URL`
   - `anon public` key → `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `service_role` key → **NO subir al frontend** (solo backend/CI si hace falta)
   - Pegar en `apps/web/.env.local` (gitignored). El template está en `apps/web/.env.example`.

3. **Correr la migración inicial**
   - Dashboard → SQL Editor → New query
   - Copiar/pegar `supabase/migrations/0001_initial_schema.sql`
   - Run

4. **Configurar Auth**
   - Authentication → Providers → Email
     - Enable email provider: ✅
     - Confirm email: ❌ (para R1: magic link directo)
   - Authentication → URL Configuration
     - Site URL: `https://sica-web.vercel.app`
     - Redirect URLs (add):
       - `https://sica-web.vercel.app/auth/callback`
       - `http://localhost:3000/auth/callback`

5. **Verificar bucket `pdfs`**
   - Storage → Buckets → debe aparecer `pdfs` (privado).
   - Si no apareció, ejecutar la sección 5 de la migración por separado.

6. **Configurar env vars en Vercel** (proyecto `sica-web`)
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `NEXT_PUBLIC_API_URL=https://sica-api-d1gq.onrender.com`
   - `NEXT_PUBLIC_API_MODE=live`

## Estructura

```
supabase/
├── README.md             ← este archivo
└── migrations/
    └── 0001_initial_schema.sql
```

Las migraciones son SQL plano y se aplican manualmente vía el SQL Editor en
el Dashboard. Cuando el CLI/MCP esté conectado, se reemplazará por `supabase db push`.

## Tablas

| Tabla | Propósito | Notas |
|---|---|---|
| `public.pacientes` | Gestantes/pacientes registradas por cada médico | `user_id` referencia `auth.users`. RLS scoped por `user_id` |
| `public.controles` | Cada PDF procesado es un control prenatal | Guarda `resumen_json` (ObstetricSummary) completo + metadata operacional |

## Row Level Security

Política única por tabla: `auth.uid() = user_id`. Cada médico solo ve sus
propios pacientes y controles. El `service_role` los puede ver todos —
usar solo en server-side jobs autorizados.

## Storage

Bucket privado `pdfs` con path convention `{user_id}/{paciente_id}/{control_id}.pdf`.
Las policies validan que la primera carpeta del path coincide con `auth.uid()`.
