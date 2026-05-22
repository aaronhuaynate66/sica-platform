# Deploy de `apps/api` a Render

Checklist para configurar el primer deploy de `sica-api` en Render. La mayoría de la configuración está declarada en `render.yaml` (raíz del repo); este documento describe **qué pulsar en la UI de Render** y qué env vars setear manualmente.

> **Pre-requisito:** El repo `aaronhuaynate66/sica-platform` está pusheado a GitHub con `render.yaml` en la raíz.

---

## 1. Crear el Web Service

1. Login en <https://dashboard.render.com>.
2. Click **"New +"** (arriba a la derecha) → **"Web Service"**.
3. **"Build and deploy from a Git repository"** → click **"Next"**.
4. Conectar GitHub si es la primera vez. Dar acceso a `aaronhuaynate66/sica-platform`.
5. En la lista de repos, click **"Connect"** en `sica-platform`.

## 2. Configurar el servicio

Render debería detectar `render.yaml` en la raíz y **preconfigurar todos los campos**. Si lo ves, click **"Apply"** y saltá a **Sección 3 (Env Vars)**.

Si Render NO detecta el blueprint (caso fallback), configurá manualmente con estos valores literales:

| Campo | Valor exacto |
|---|---|
| **Name** | `sica-api` |
| **Project** | (dejar en blanco o crear uno nuevo "SICA") |
| **Language** | `Python 3` ⚠️ NO Node, NO Docker |
| **Branch** | `main` |
| **Region** | `Oregon (US West)` |
| **Root Directory** | `apps/api` ⚠️ **CRÍTICO** |
| **Build Command** | `pip install --upgrade pip && pip install -e .` |
| **Start Command** | `uvicorn sica_api.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | `Free` |
| **Health Check Path** | `/health` |

> El plan **Free** duerme tras 15 minutos sin tráfico — el primer request post-sleep tarda ~30s. Para staging/preview es aceptable; producción requiere upgrade.

## 3. Environment Variables

En la sección **"Environment Variables"** (durante creación o después en Settings → Environment), agregar:

| Name | Value | Notas |
|---|---|---|
| `ANTHROPIC_API_KEY` | _(pegar la API key real)_ | ⚠️ **Secreto**. Render lo cifra at rest. NUNCA commitear. |
| `LOG_LEVEL` | `INFO` | |
| `MAX_FILE_SIZE_MB` | `10` | Tope del PDF aceptado por `/extract`. |
| `ALLOWED_ORIGINS` | `https://sica-web.vercel.app,https://*.vercel.app,http://localhost:3000` | Lista CSV de orígenes literales. El wildcard `*.vercel.app` es informativo — el match real lo hace `ALLOWED_ORIGIN_REGEX`. |
| `ALLOWED_ORIGIN_REGEX` | `^https://([a-z0-9-]+\.)*vercel\.app$` | Regex que cubre los preview deploys de Vercel con hash random. |
| `PYTHON_VERSION` | `3.13.0` | Pin de la runtime. `render.yaml` también lo declara via `pythonVersion: "3.13"`. |

> ⚠️ La env var `PORT` la inyecta Render automáticamente — **NO la declares manualmente**.

## 4. Deploy

Click **"Create Web Service"** (o **"Apply"** si Render detectó el blueprint).

- Build: 2-4 min (`pip install -e .` resuelve fastapi, uvicorn, anthropic, pypdf, pydantic).
- Deploy: 30-60s adicionales para arrancar el contenedor.
- Render asigna la URL: **`https://sica-api.onrender.com`** (el subdominio coincide con el nombre del servicio).

Logs en vivo durante el build se ven en la pestaña **"Logs"** del servicio.

## 5. Verificar

Una vez que el banner verde **"Live"** aparece arriba a la izquierda:

```bash
curl https://sica-api.onrender.com/health
```

**Respuesta esperada** (HTTP 200):

```json
{
  "status": "ok",
  "version": "0.1.0",
  "extractor_available": true,
  "timestamp": "2026-05-22T15:30:00Z"
}
```

- `extractor_available: true` confirma que `ANTHROPIC_API_KEY` está configurada.
- Si es `false` → revisar la env var en Render UI y forzar redeploy.

Verificar `/models`:

```bash
curl https://sica-api.onrender.com/models | head -c 200
```

Debe devolver un array con 7 modelos según ADR 0004.

Verificar CORS preflight desde el dominio de Vercel:

```bash
curl -i -X OPTIONS https://sica-api.onrender.com/extract \
  -H "Origin: https://sica-web.vercel.app" \
  -H "Access-Control-Request-Method: POST"
```

Debe devolver `access-control-allow-origin: https://sica-web.vercel.app`.

## 6. Conectar la UI

Una vez que la API está live, **actualizar Vercel** para apuntar a Render:

1. En Vercel → Project `sica-web` → Settings → Environment Variables.
2. Editar:
   - `NEXT_PUBLIC_API_URL` → `https://sica-api.onrender.com`
   - `NEXT_PUBLIC_API_MODE` → `live`
3. Trigger redeploy: Vercel UI → Deployments → ⋯ → **Redeploy**.
4. Abrir `https://sica-web.vercel.app` y verificar que el badge dice **"Live mode"** (verde) y que el botón **"Subir PDF propio"** ahora funciona (no muestra el mensaje demo).

## 7. Troubleshooting

| Síntoma | Causa probable | Acción |
|---|---|---|
| Build error `Python 3.13 not available` | Free tier puede estar en una versión más vieja. | En Settings → Environment, override `PYTHON_VERSION=3.13.0`. Si Render no lo soporta aún, bajar a `3.12.0` temporalmente. |
| `ImportError: No module named clinical_extractor` | `pip install -e .` no instaló transitivamente. | Render no tiene acceso al monorepo entero por defecto — `apps/api` no depende explícitamente del extractor para arrancar (sólo lo necesita en `/extract`). Si querés `/extract` funcional, agregar el extractor como dep instalable (Docker, o publicar a registry interno). |
| `/health` devuelve 503 | App no arrancó. | Pestaña **Logs** → revisar último traceback. Lo más común: env var faltante o version mismatch. |
| CORS bloquea desde Vercel | `ALLOWED_ORIGIN_REGEX` mal escapado. | Verificar que el valor en Render UI es exactamente `^https://([a-z0-9-]+\.)*vercel\.app$` con un solo backslash en `\.`. |
| Free tier dormido — primer request lento | Comportamiento esperado. | Upgrade a plan pago para "always on", o pingear `/health` cada 14 min desde un cron externo (no se hace desde la propia app). |

## Referencias

- [Render — Blueprint Spec](https://render.com/docs/blueprint-spec) (el formato de `render.yaml`)
- [Render — Python Web Services](https://render.com/docs/deploy-fastapi)
- [Render — Free Tier Limits](https://render.com/docs/free)
- `render.yaml` (raíz del repo) — configuración canónica
- `apps/api/.python-version` — pin de runtime
- `apps/api/.env.example` — vars equivalentes para desarrollo local
