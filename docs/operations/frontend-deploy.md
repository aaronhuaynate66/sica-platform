# Deploy del frontend SICA en Vercel

Esta guía cubre el deploy **post-R1** (Supabase + magic link auth + upload real).
Para el bootstrap inicial del proyecto Vercel, ver `apps/web/VERCEL.md`.

## 1. Variables de entorno en Vercel

Project `sica-web` → Settings → Environment Variables. Reemplazar los valores
demo con los reales:

| Name | Value | Environments |
|---|---|---|
| `NEXT_PUBLIC_API_MODE` | `live` | Production · Preview · Development |
| `NEXT_PUBLIC_API_URL` | `https://sica-api-d1gq.onrender.com` | Production · Preview · Development |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://<proj-ref>.supabase.co` | Production · Preview · Development |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `<anon-key>` | Production · Preview · Development |

> **NO subir** el `service_role` key. El frontend solo necesita la `anon` key —
> las policies RLS hacen el aislamiento. Si en futuro hay server jobs que
> requieran service_role, se montarán en un servicio separado.

### Vía CLI (opcional)

```powershell
cd apps/web
vercel link        # si no está linkeado todavía
vercel env add NEXT_PUBLIC_SUPABASE_URL production
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production
vercel env add NEXT_PUBLIC_API_MODE production   # value: live
vercel env add NEXT_PUBLIC_API_URL production    # value: https://sica-api-d1gq.onrender.com
```

Repetir para `preview` y `development` si querés que los previews también
apunten a la misma base.

## 2. Configurar Supabase Auth con la URL de Vercel

En Supabase Dashboard → Authentication → URL Configuration:

- **Site URL**: `https://sica-web.vercel.app`
- **Additional Redirect URLs**:
  - `https://sica-web.vercel.app/auth/callback`
  - `http://localhost:3000/auth/callback`
  - Si hay dominio custom, agregar `https://<dominio>/auth/callback`.

Esto es **bloqueante** para que el magic link funcione en producción.

## 3. Deploy

`git push origin main` activa el auto-deploy de Vercel. Esperar 2-4 minutos.

Verificar en `https://vercel.com/<team>/sica-web/deployments` que el build
termina en verde.

## 4. Smoke E2E manual

URL: `https://sica-web.vercel.app`

1. `/login` → ingresar email del médico → click "Enviar enlace".
2. Revisar email → click magic link → debe redirigir a `/app`.
3. `/app` muestra la tabla de pacientes (vacía la primera vez).
4. Click "Subir control" → cargar `services/clinical-extractor/data/longitudinal_lucia_sem16.pdf`.
5. Elegir "Nuevo paciente" → completar nombre. Submit.
6. Esperar 30-50s (cold start Render + extracción). Debe redirigir al detalle del control.
7. Verificar que aparecen: datos demográficos, problemas activos, factores de riesgo, labs, notas, evidencia.
8. Volver al paciente → subir `longitudinal_lucia_sem24.pdf` al mismo paciente.
9. Timeline muestra 2 controles.
10. Click "Comparar" → diff visible (problemas agregados, labs evolución).

## 5. Invitar al médico colaborador

Una vez que el smoke esté en verde:

1. Compartir la URL `https://sica-web.vercel.app/login` con el médico.
2. El médico ingresa su email institucional.
3. Recibe el magic link y entra.

No hay aprobación previa — Supabase Auth crea el usuario en el primer login.
Si querés restringir el acceso solo a emails específicos, agregar una policy
adicional en Supabase Auth (Dashboard → Authentication → Settings → "Allowed
email domains") o filtrar en el middleware.

## 6. Monitoreo de uso

- **Supabase Dashboard**: Project → Reports → API requests, Storage usage, MAU.
- **Langfuse**: traces de cada `/extract` con el `request_id` (= `trace_id` de la fila).
- **Vercel Dashboard**: Function invocations + bandwidth + build minutes.

## 7. Rollback

Si un deploy rompe en producción:

```powershell
vercel rollback https://sica-web.vercel.app
```

O desde la UI: Deployments → click el deploy bueno previo → "Promote to Production".

## 8. TODOs operativos pendientes

- [ ] Configurar custom domain (e.g. `sica.example.pe`) cuando se firme partner.
- [ ] CORS de `apps/api` (Render) — confirmar que `allowed_origin_regex` matchea `sica-web.vercel.app`.
- [ ] CronJob de cleanup de PDFs huérfanos en Storage (controles que fallaron).
- [ ] Restringir email domains permitidos cuando el partner clínico exija.
