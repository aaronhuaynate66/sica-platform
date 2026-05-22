# Deploy de `apps/web` a Vercel

Checklist exacto para configurar el primer deploy. **Este documento describe acciones manuales en la UI de Vercel** — no las podés automatizar sin un token, y la primera vez vale la pena hacerlas a mano para entender qué quedó conectado.

> **Pre-requisito:** El repo `aaronhuaynate66/sica-platform` está pusheado a GitHub con el commit que contiene este archivo.

---

## 1. Crear el proyecto en Vercel

1. Abrí <https://vercel.com/login> y entrá con la cuenta de GitHub asociada al repo.
2. En el dashboard, click **"Add New…" → "Project"**.
   - URL directa: <https://vercel.com/new>
3. Buscá el repo `aaronhuaynate66/sica-platform` y click **"Import"**.
   - Si no aparece: click **"Adjust GitHub App Permissions"** y dale acceso a este repo.

## 2. Configurar el import

Vercel te pregunta qué deployar. Esta es la parte importante:

| Campo | Valor exacto |
|---|---|
| **Project Name** | `sica-web` (o el que prefieras — define la URL `*.vercel.app`) |
| **Framework Preset** | `Next.js` (debería auto-detectarse) |
| **Root Directory** | `apps/web` ⚠️ **crítico** — click "Edit" y poner exactamente esto |
| **Build Command** | _dejarlo en blanco / "Override" desactivado_ — `vercel.json` lo provee |
| **Output Directory** | _dejarlo en blanco_ — `vercel.json` lo provee |
| **Install Command** | _dejarlo en blanco_ — `vercel.json` lo provee |
| **Node.js Version** | `20.x` (o lo que esté seleccionado por default) |

> Si Vercel insiste en un Install Command, podés escribir literalmente `echo skip` — el `buildCommand` de `vercel.json` se encarga de `pnpm install`.

## 3. Environment Variables

En la misma pantalla de import, expandir **"Environment Variables"** y agregar dos:

| Name | Value | Environments |
|---|---|---|
| `NEXT_PUBLIC_API_MODE` | `demo` | ✅ Production · ✅ Preview · ✅ Development |
| `NEXT_PUBLIC_API_URL` | `https://api.sica.example.com` | ✅ Production · ✅ Preview · ✅ Development |

> El valor de `NEXT_PUBLIC_API_URL` es un **placeholder**: aún no existe la API pública. Mientras `NEXT_PUBLIC_API_MODE=demo`, la UI nunca llama al backend, así que el placeholder no rompe nada. Cambiar ambos a `live` + URL real cuando el deploy de `apps/api` esté listo (Cloud Run pendiente).

## 4. Deploy

Click **"Deploy"**. El primer build tarda 2-4 minutos.

Mientras builda, Vercel muestra logs en vivo. Si todo va bien, al final:
- Vercel asigna automáticamente `https://sica-web-<random>.vercel.app` (preview) y `https://<project-name>.vercel.app` (production).
- Pone un check verde en el commit en GitHub.

## 5. Verificar el deploy

Una vez listo el deploy:

1. **Abrir la URL de production** (la que termina en `<project>.vercel.app`).
2. **Verificar visualmente:**
   - El header dice "SICA" arriba con nav: Upload / Timeline / Dashboard / Physician.
   - El badge **"Demo mode"** está en amarillo (porque `NEXT_PUBLIC_API_MODE=demo`).
   - Pulsar **"Cargar PDF de ejemplo"** → aparece el PDF + el panel JSON con todas las cards (Confianza, Datos gestacionales, Problemas activos, Laboratorios, Resumen y plan).
   - Pulsar **"Subir PDF propio"** → seleccionar cualquier PDF → debe aparecer el mensaje: _"Modo demo: subir PDFs propios requiere API conectada. Usa el ejemplo o solicita acceso."_
   - El disclaimer en la barra inferior sigue visible: _"Datos sintéticos · No es paciente real · No clínicamente validado"_.
3. **Verificar el resto de las vistas:**
   - `/timeline` carga timeline gestacional.
   - `/dashboard` carga la tabla densa de pacientes.
   - `/physician` carga el panel del médico.

## 6. (Opcional) Dominio custom

Si querés `sica.example.com` en lugar de `*.vercel.app`:

1. **Project → Settings → Domains**.
2. **"Add"** → escribí el dominio.
3. Vercel te dice qué record DNS agregar (CNAME o A). Hacelo en el registrador.
4. Esperar propagación (5-60 min) → Vercel emite SSL automático (Let's Encrypt).

Cuando exista el dominio real:
- Editar `apps/api/src/sica_api/settings.py` → `allowed_origin_regex` debe incluir ese dominio.
- Editar `NEXT_PUBLIC_API_URL` en Vercel UI → apuntar al backend real.

## 7. Si algo falla

| Síntoma | Acción |
|---|---|
| Build error "command not found pnpm" | Vercel detecta pnpm via `packageManager` en `package.json` raíz o `pnpm-lock.yaml`. Si no, en Project Settings → General → "Install Command" forzar `npm i -g pnpm@11.1.2 && pnpm install --frozen-lockfile`. |
| Build error "lockfile out of sync" | Hacer `pnpm install` local, commitear el `pnpm-lock.yaml`, push, redeploy. |
| Deploy OK pero 404 en `/` | Confirmar que **Root Directory = `apps/web`**. Si está en blanco, Vercel buscará Next en la raíz y no lo encontrará. |
| Logs muestran `output: standalone` symlink errors | NO debería pasar — `next.config.ts` deliberadamente NO usa `standalone`. Si aparece, alguien lo agregó de vuelta. |
| Badge dice "Live mode" en producción | Verificar que `NEXT_PUBLIC_API_MODE=demo` en Production env. Vercel inyecta vars al bundle en build-time. |

## Referencias

- [Vercel — Monorepo Guide](https://vercel.com/docs/monorepos)
- [Vercel — Project Configuration](https://vercel.com/docs/project-configuration)
- [Vercel — Ignored Build Step](https://vercel.com/docs/projects/git-integration#ignored-build-step)
- `apps/web/vercel.json` — config canónica del proyecto.
- `.vercelignore` (raíz) — qué archivos NO sube Vercel.
- `apps/web/.env.example` — vars de entorno que la UI lee.
