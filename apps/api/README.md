# sica-api

Backend HTTP de SICA. Expone el `clinical-extractor` como API REST y servirá como punto de orquestación para los próximos servicios (handoff, brief preanestésico, care gaps).

**Estado:** R0 — bootstrap inicial. No usar contra PHI real hasta que estén activos auth, audit logs, rate limit y el extractor migre fuera de Claude (ver [ADR 0003](../../docs/decisions/0003-security-and-phi-policy.md) y [ADR 0004](../../docs/decisions/0004-model-routing-policy.md)).

## Endpoints

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/health` | Liveness + readiness. Reporta `extractor_available`. |
| `GET` | `/models` | Lista declarativa de modelos según ADR 0004. |
| `POST` | `/extract` | Multipart `file` (PDF) → `ObstetricSummary` JSON. |

### `GET /health`

```json
{ "status": "ok", "version": "0.1.0", "extractor_available": true }
```

`extractor_available=false` cuando `ANTHROPIC_API_KEY` no está configurada. `/extract` devuelve 503 en ese caso.

### `GET /models`

Devuelve un array con cada modelo declarado en la política de routing. Cada item:

```json
{
  "id": "medgemma-4b",
  "provider": "google",
  "type": "local",
  "phi_allowed": true,
  "active": false,
  "role": "default",
  "notes": "..."
}
```

La lista es **estática en R0** (hard-coded desde ADR 0004 Nivel 1). En R1+ pasará a leer del registry vivo del orquestador.

### `POST /extract`

Request: `multipart/form-data` con campo `file` (PDF, max `MAX_FILE_SIZE_MB`).

Respuestas:

| Code | Cuando |
|---|---|
| `200` | Extracción OK. Body = `ObstetricSummary` JSON. |
| `400` | No es PDF (content-type o magic bytes), o body vacío. |
| `413` | Archivo excede `MAX_FILE_SIZE_MB`. |
| `422` | Body multipart inválido o falta `file`. |
| `500` | Fallo interno. Body incluye `error_id` para correlación. Stack trace NUNCA se expone. |
| `503` | `ANTHROPIC_API_KEY` ausente. |

Todas las respuestas incluyen header `X-Request-ID`. Errores 5xx adicionalmente incluyen `X-Error-ID`. El cliente debe loggear ambos.

**El output es asistivo. Debe ser revisado por un médico antes de cualquier uso clínico.**

## Run local

Setup en el directorio `apps/api/`:

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows: PowerShell o Git Bash
# o: source .venv/bin/activate   # Linux / macOS

pip install -e ".[dev]"
# Para llamar al extractor real, además:
pip install -e ../../services/clinical-extractor

cp .env.example .env
# Editar .env y poner ANTHROPIC_API_KEY=...

uvicorn sica_api.main:app --reload --port 8000
```

Smoke rápido con curl:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/models

curl -X POST http://localhost:8000/extract \
  -F "file=@../../services/clinical-extractor/data/synthetic_case_01.pdf"
```

Documentación interactiva (Swagger UI): http://localhost:8000/docs

## Tests

```bash
pytest -q
```

Los tests **no llaman al modelo real**. El extractor se reemplaza vía `app.dependency_overrides[get_extractor]` con un fake configurado en `conftest.py`. Cualquier llamada al API de Anthropic dentro de un test es un bug.

## Settings

Variable `.env` → atributo de `Settings`. Defaults se aplican si la variable no está presente.

| Variable | Default | Descripción |
|---|---|---|
| `ANTHROPIC_API_KEY` | _(vacío)_ | Si vacío, `/extract` → 503. |
| `MAX_FILE_SIZE_MB` | `10` | Límite por upload. |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS allow-list, comma-separated. |
| `LOG_LEVEL` | `INFO` | `DEBUG | INFO | WARNING | ERROR` |

## Próximos pasos

- **Auth.** R0 corre sin auth — sólo para uso local del founder y CI. Antes de exponer a partner: JWT/OIDC + tenant claim + RBAC.
- **Rate limit.** Anti-abuso a nivel gateway (NGINX/Cloudflare) más rate limit por usuario en la app.
- **Audit trail.** Implementar Nivel 4 de ADR 0004 — registrar cada llamada a `/extract` en append-only audit log (sin contenido del PDF, sólo hashes).
- **Observabilidad.** OpenTelemetry + Sentry + métricas latencia/error por endpoint. Sentry hookup va con issue #14 (Langfuse).
- **PHI hardening.** Migrar `/extract` a MedGemma local cuando #12 cierre. Hasta entonces este endpoint es para datos sintéticos / desidentificados.
- **Orquestador.** Agregar `/handoff`, `/brief-anestesia`, `/care-gaps` cuando los servicios correspondientes existan (R3+).

## Referencias internas

- [`STRATEGY.md` § 11](../../STRATEGY.md) — Arquitectura técnica.
- [ADR 0003](../../docs/decisions/0003-security-and-phi-policy.md) — Security and PHI handling.
- [ADR 0004](../../docs/decisions/0004-model-routing-policy.md) — Política de routing de modelos.
- [`services/clinical-extractor/README.md`](../../services/clinical-extractor/README.md) — Servicio que esta API consume.
