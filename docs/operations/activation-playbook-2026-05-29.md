# Playbook de activación SICA — 2026-05-29

> Documento operacional. Pasos manuales para activar el frontend SICA en producción y desbloquear el primer uso real con el médico colaborador.
>
> **Tiempo estimado total:** 25–35 minutos.
> **Pre-requisitos:** acceso a Supabase, Vercel, GitHub (owner del repo).

---

## Resumen ejecutivo

3 servicios externos a configurar:
1. **Supabase** — proyecto nuevo + schema SQL + auth.
2. **Vercel** — 4 env vars + redeploy.
3. **GitHub Actions** — 3 secrets para el workflow `langfuse-cleanup`.

Después: **smoke E2E con dataset Lucía** (10 min).

---

## Checklist global

```
☐ Paso 1  — Supabase project creado
☐ Paso 2  — SQL migration aplicada
☐ Paso 3  — Supabase auth configurada (Site URL + Redirect URLs + Email provider)
☐ Paso 4  — Project URL + anon key copiados
☐ Paso 5  — Vercel env vars agregadas (4 vars)
☐ Paso 6  — Vercel redeploy ejecutado
☐ Paso 7  — GitHub secrets de Langfuse agregados (3 secrets)
☐ Paso 8  — Smoke E2E: login con magic link funciona
☐ Paso 9  — Smoke E2E: paciente Lucía creado
☐ Paso 10 — Smoke E2E: sem16 procesado
☐ Paso 11 — Smoke E2E: sem24 procesado
☐ Paso 12 — Smoke E2E: timeline + comparador
☐ Paso 13 — (Opcional) Dry-run manual del workflow Langfuse cleanup
```

---

## Paso 1 — Crear proyecto Supabase

1. Abrir <https://supabase.com/dashboard/projects>.
2. **New project**:
   - **Name:** `sica-platform`
   - **Database password:** generar fuerte (16+ chars). Copiar a 1Password / Bitwarden.
   - **Region:** `South America (São Paulo)` (`sa-east-1`).
   - **Plan:** Free.
3. **Create new project**.
4. Esperar ~2 min al setup. La UI muestra "Setting up project..." y luego "Project is ready".

---

## Paso 2 — Aplicar schema SQL

1. Sidebar izquierdo → **SQL Editor**.
2. **New query**.
3. Abrir en local: `supabase/migrations/0001_initial_schema.sql`.
4. Copiar **TODO** el contenido → pegar en el SQL Editor de la UI.
5. **Run** (botón verde).
6. Verificar respuesta: `"Success. No rows returned"`.

### Troubleshooting

- **Error de permisos**: verificar que tu usuario es owner del proyecto.
- **Error de syntax**: copiar el error completo y reportar; el SQL debe estar limpio.
- **Error `extension does not exist`**: el SQL usa `gen_random_uuid()` que requiere `pgcrypto`. Ejecutar primero `CREATE EXTENSION IF NOT EXISTS pgcrypto;` y reintentar.

---

## Paso 3 — Configurar Auth

### 3.1 URL Configuration

Sidebar → **Authentication → URL Configuration**:

- **Site URL:** `https://sica-web.vercel.app` (sin trailing slash).
- **Redirect URLs** (botón **Add URL** para cada una):
  - `https://sica-web.vercel.app/auth/callback`
  - `http://localhost:3000/auth/callback`

**Save**.

### 3.2 Email Provider

Sidebar → **Authentication → Providers → Email**:

- **Enable Email provider:** ON
- **Confirm email:** OFF — importante. Permite magic link directo sin paso intermedio de confirmación.

**Save**.

---

## Paso 4 — Copiar credenciales

Sidebar → **Project Settings → API**. Copia a notepad temporal:

- **Project URL** (formato `https://xxxxxxxxxxxx.supabase.co`).
- **anon public** key (formato `eyJxxx...` — JWT corto).

> **No copies `service_role` key.** No se usa en frontend y exponerla en `NEXT_PUBLIC_*` rompe la garantía de RLS.

---

## Paso 5 — Vercel env vars

1. <https://vercel.com/dashboard> → proyecto **sica-web**.
2. **Settings → Environment Variables**.
3. Agregar las 4 (botón **Add** una por una):

| Key | Value | Environments |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Project URL del Paso 4 | Production, Preview, Development |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | anon key del Paso 4 | Production, Preview, Development |
| `NEXT_PUBLIC_API_URL` | `https://sica-api-d1gq.onrender.com` | Production, Preview, Development |
| `NEXT_PUBLIC_API_MODE` | `live` | Production, Preview, Development |

> El valor `live` hace que el frontend intente el backend Render y caiga a `demo` si `/health` falla. Para forzar siempre demo (sin tocar Render), usar `demo`.

---

## Paso 6 — Redeploy Vercel

1. Tab **Deployments**.
2. Último deploy → menú "⋮" → **Redeploy**.
3. **Use existing build cache:** desmarcar (para asegurar que las env nuevas se inyectan).
4. **Redeploy**.
5. Esperar ~2 min al build + deploy.

---

## Paso 7 — GitHub secrets para Langfuse cleanup

GitHub → repo `sica-platform` → **Settings → Secrets and variables → Actions** → **New repository secret**.

Agregar 3 secrets (los valores los tienes en el `.env` local del extractor o en el Render dashboard del servicio `sica-api`):

| Name | Value |
|---|---|
| `LANGFUSE_BASE_URL` | `https://us.cloud.langfuse.com` |
| `LANGFUSE_PUBLIC_KEY` | `pk-lf-...` (del proyecto Langfuse usado por el extractor) |
| `LANGFUSE_SECRET_KEY` | `sk-lf-...` (del mismo proyecto) |

> **Importante:** las credenciales deben ser del **mismo proyecto Langfuse** donde Render envía traces. Si apuntan a otro proyecto, el cleanup actúa sobre traces equivocadas.

Sin estos secrets, el cron del domingo del workflow `langfuse-cleanup` fallará en el step "Run cleanup". No es urgente para R1 (la primera retención efectiva es a 180 días), pero conviene configurar hoy.

---

## Paso 8 — Smoke E2E: login con magic link

1. Abrir <https://sica-web.vercel.app/login>.
2. Ingresar tu email (`aaronhuaynate@gmail.com` o equivalente).
3. Click **Enviar magic link**.
4. Revisar inbox → click en el link.
5. Debes aterrizar en `/app`.

### Troubleshooting

- **No llega el email**: verificar spam folder. Confirmar **Confirm email = OFF** en Supabase Auth (Paso 3.2). Esperar 2 min — Supabase puede tardar.
- **Redirect roto** (URL inválida después del click): verificar que `Site URL = https://sica-web.vercel.app` exacto, sin trailing slash. Confirmar `Redirect URLs` incluye `/auth/callback`.

---

## Paso 9 — Smoke E2E: crear paciente Lucía

En `/app`:

1. Click **Subir control** o **Nuevo paciente**.
2. Crear paciente:
   - **Nombre:** `Lucia Mendoza Quispe`
   - **DNI:** `47812936`
   - **Fecha nacimiento:** `1996-03-15`

> Estos datos son sintéticos (paciente de fixture). NO necesitan consentimiento.

---

## Paso 10 — Smoke E2E: procesar sem16

1. Seleccionar paciente Lucía recién creada.
2. Subir archivo: `services/clinical-extractor/data/longitudinal_lucia_sem16.pdf`.
3. **Esperar ~30s** — Render free tier puede cold-start.
4. Verificar la vista del control con:
   - `gestational_age_weeks ≈ 16`
   - `active_problems` incluye "Sobrepeso pre-gestacional"
   - `confidence_score ≥ 0.85`

**Costo Anthropic:** ~USD 0.04.

---

## Paso 11 — Smoke E2E: procesar sem24

Mismo flujo con `longitudinal_lucia_sem24.pdf`.

Verificaciones:
- La paciente ahora tiene 2 controles.
- El nuevo control muestra `gestational_age_weeks ≈ 24`.
- `active_problems` incluye `Diabetes gestacional` (DG diagnosticada en sem24).

**Costo Anthropic:** ~USD 0.04.

---

## Paso 12 — Smoke E2E: timeline + comparador

1. Navegar a la vista de Lucía (lista de pacientes → click).
2. Verificar **timeline** muestra los 2 controles ordenados por fecha.
3. Click **Comparar** → seleccionar sem16 y sem24.
4. Verificar diff visual:
   - `active_problems` agregadas en sem24 (DG diagnosticada).
   - Cambios en `lab_results` (PTOG alterada, glucemias).
   - Evolución de peso, AU, FCF entre controles.

Si el comparador renderiza limpio y los diffs son interpretables, **el flujo end-to-end funciona**.

---

## Paso 13 — (Opcional) Dry-run manual del workflow Langfuse cleanup

Validación de que los secrets del Paso 7 quedaron OK.

1. GitHub → repo → tab **Actions**.
2. Sidebar → **Langfuse Retention Cleanup**.
3. Botón **Run workflow** (esquina superior derecha):
   - **Branch:** `main`
   - **execute:** `false`
   - **retention_days:** vacío
4. **Run workflow**.
5. Esperar ~1–2 min.
6. Abrir el run → descargar artifact `cleanup-report-{run_id}`.
7. Abrir el JSON. Si `inspected: 0` y `errors: []`, los secrets están OK pero todavía no hay traces > 180 días (esperado en R1 reciente).

---

## Troubleshooting general

### Magic link no llega
- **Confirm email** debe estar OFF (Paso 3.2).
- Revisar spam folder.
- Reintentar después de 2 min — Supabase free tier puede tardar.

### Login redirect roto
- **Site URL** exacto: `https://sica-web.vercel.app` (sin trailing slash).
- **Redirect URLs** incluye `/auth/callback`.

### Upload PDF da 500
- Probable cold start Render. Reintentar 1 vez.
- Si persiste: revisar logs en Render dashboard del servicio `sica-api`.

### Timeline vacío después de subir
- RLS bloqueando reads → revisar que `user_id` en `controles` coincida con `auth.uid()` actual.
- Validar desde Supabase SQL Editor:
  ```sql
  SELECT id, user_id, paciente_id, created_at FROM public.controles ORDER BY created_at DESC LIMIT 5;
  ```

### CORS error en console del browser
- CORS debe permitir `*.vercel.app` (ya configurado en `apps/api`).
- Si persiste: verificar `NEXT_PUBLIC_API_URL` exacto sin trailing slash.

### Bucket `pdfs` ausente
- La migration debería haberlo creado. Si no existe, ejecutar la sección 5 del SQL por separado.
- Confirmar en Supabase → Storage → Buckets.

---

## Después del smoke exitoso

1. **Invitar al médico colaborador**:
   - Compartir `https://sica-web.vercel.app/login`.
   - Indicarle que ingrese su email y revisar inbox para el magic link.

2. **Conversación operacional** (cubrir antes del primer PDF real):
   - Convención de filenames: renombrar a `caso_{fecha}_{secuencial}.pdf` antes de subir (evita PHI en logs locales).
   - Cómo correlacionar `trace` en Langfuse → paciente real (cruzar `request_id` con logs locales del API + hoja de tracking propia).
   - Consentimiento informado con la paciente: documento físico/digital firmado, registro auditable separado del sistema.

3. **Observar primer uso real**:
   - **Langfuse dashboard**: verificar visualmente que `[REDACTED]` aparece en campos PHI.
   - **Vercel logs**: confirmar magic link enviado, upload exitoso.
   - **Supabase Auth → users**: debe aparecer el email del médico.
   - **Supabase tabla `controles`**: debe aparecer su primer caso real con `resumen_json` completo.

---

## Rollback si algo crítico falla

Si después del smoke encuentras bugs irrecuperables hoy:

1. **NO mergear nada nuevo a main** hasta arreglar.
2. Documentar bug en `docs/operations/bug-2026-05-29.md` (filename con fecha).
3. Decidir entre:
   - **Rollback del último deploy Vercel** (1 click desde Deployments → ⋮ → Rollback). Reversible.
   - **Forward fix** en main + redeploy.
4. **El backend Render NO se afecta** — sigue funcional independiente de Vercel.

---

## Lo que NO debes hacer hoy

- No procesar PDF con datos reales de paciente sin consentimiento firmado.
- No compartir el `service_role` key con nadie ni ponerlo en frontend.
- No cambiar la migration SQL después de aplicada (siempre nueva migration).
- No disparar workflow `Langfuse Retention Cleanup` con `execute=true` (espera al menos a que haya traces > 180 días — primer execute útil ~mes 12).
- No modificar archivos `extract_obstetric_v1.md` o `extract_obstetric_v2.md` in-place (crear v3 si se quiere cambiar — los tests del registry te van a frenar igual).

---

## Referencias

- [supabase/README.md](../../supabase/README.md) — bootstrap canónico del proyecto Supabase.
- [supabase/migrations/0001_initial_schema.sql](../../supabase/migrations/0001_initial_schema.sql) — schema completo.
- [apps/web/.env.example](../../apps/web/.env.example) — template de env vars del frontend.
- [docs/operations/frontend-deploy.md](frontend-deploy.md) — guía de deploy a Vercel.
- [docs/operations/langfuse-retention.md](langfuse-retention.md) — política de retención (setup de secrets + ejecución).
- [docs/operations/phi-handling.md](phi-handling.md) — manejo de PHI antes del primer PDF real.
- [docs/decisions/0011-frontend-stack.md](../decisions/0011-frontend-stack.md) — decisión del stack frontend.
