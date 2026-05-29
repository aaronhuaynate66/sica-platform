# sica-api

Backend HTTP de SICA. Expone el `clinical-extractor` como API REST y servirá como punto de orquestación para los próximos servicios (handoff, brief preanestésico, care gaps).

**Estado:** R0 — bootstrap inicial. No usar contra PHI real hasta que estén activos auth, audit logs, rate limit y el extractor migre fuera de Claude (ver [ADR 0003](../../docs/decisions/0003-security-and-phi-policy.md) y [ADR 0004](../../docs/decisions/0004-model-routing-policy.md)).

## Endpoints

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/health` | Liveness + readiness. Reporta `extractor_available`. |
| `GET` | `/models` | Lista plana de modelos según ADR 0004 (retrocompatible). |
| `GET` | `/providers` | Shape rico agrupado por provider con modelos, capabilities y availability. |
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

La lista es **estática en R0** (hard-coded desde ADR 0004 Nivel 1) cruzada con el estado runtime del registry de providers (`is_available`, `provider_id`). En R1+ pasará a leer del registry vivo del orquestador.

### `GET /providers`

Vista jerárquica de los `LLMProvider` registrados en `clinical_extractor.providers.DEFAULT_REGISTRY`, junto con los modelos que cada uno soporta, sus capabilities y por qué un provider no está operativo (cuando aplique). Diseñado para UIs nuevas o dashboards que necesiten estructura completa.

Response:

```json
{
  "providers": [
    {
      "provider_id": "anthropic",
      "is_available": true,
      "available_note": null,
      "models": [
        {"id": "claude-sonnet-4-5-20250929", "is_default": true},
        {"id": "claude-opus-4-7", "is_default": false},
        {"id": "claude-haiku-4-5-20251001", "is_default": false}
      ],
      "capabilities": ["tool_use", "vision", "streaming", "long_context"]
    },
    {
      "provider_id": "vertex-medgemma",
      "is_available": false,
      "available_note": "Pendiente: GCP credentials no configuradas y extract() sin implementar. Ver issue #12 y vertex_medgemma_provider.py.",
      "models": [
        {"id": "medgemma-4b-it", "is_default": true}
      ],
      "capabilities": []
    }
  ],
  "default_provider_id": "anthropic",
  "total_providers": 2,
  "available_count": 1
}
```

Cuándo usar cada uno:

- `/providers` → UIs nuevas, dashboards, herramientas que necesitan estructura completa por provider.
- `/models` → frontend legacy y listados planos. **El shape no se cambia** — los dos endpoints conviven.

### `POST /extract`

Request: `multipart/form-data` con campo `file` (PDF, max `MAX_FILE_SIZE_MB`).

Query parameters:

| Parámetro | Default | Descripción |
|---|---|---|
| `provider` | `anthropic` | ID del provider LLM. Valores válidos: `anthropic` (default), `vertex`. `vertex` retorna 503 hasta que GCP MedGemma esté configurado (issue #12). Ver [ADR 0004 § Actualización 2026-05-27](../../docs/decisions/0004-model-routing-policy.md). |

Ejemplos:

```bash
# Default (anthropic — sin query param, preserva contrato existente)
POST /extract

# Explícito
POST /extract?provider=anthropic
POST /extract?provider=vertex   # 503 mientras vertex sea stub
```

Respuestas:

| Code | Cuando |
|---|---|
| `200` | Extracción OK. Body = `ObstetricSummary` JSON al top-level **+ campo aditivo `metadata`** con trazabilidad operacional (ver abajo). |
| `400` | No es PDF (content-type o magic bytes), body vacío, o `provider` inválido (`?provider=foo`). |
| `413` | Archivo excede `MAX_FILE_SIZE_MB`. |
| `422` | Body multipart inválido o falta `file`. |
| `500` | Fallo interno del extractor. Body incluye `error_id` para correlación. Stack trace NUNCA se expone. |
| `503` | `ANTHROPIC_API_KEY` ausente, **o** el provider seleccionado no está disponible (vertex sin GCP creds, NotImplementedError del stub). |

Shape del response 200:

```json
{
  "patient_age": 28,
  "gestational_age_weeks": 16.3,
  "fum": "2023-12-27",
  "fpp": "2024-10-03",
  "active_problems": ["Sobrepeso pre-gestacional (IMC 25.6)"],
  "risk_factors": ["Antecedente familiar DM2"],
  "lab_results": [
    { "name": "Hemoglobina", "value": "11.8", "unit": "g/dL", "date": null, "abnormal": false }
  ],
  "notes_summary": "...",
  "confidence_score": 0.95,
  "evidence_spans": [{ "claim": "...", "source_page": 1, "source_text": "..." }],

  "metadata": {
    "operation_id": "f2d8c4a0-1234-...",
    "provider_id": "anthropic",
    "model_used": "claude-sonnet-4-5-20250929",
    "prompt_version": "0.1.0",
    "prompt_hash": "9241ec0d",
    "input_tokens": 4261,
    "output_tokens": 1251,
    "cost_usd": 0.031548,
    "latency_ms": 22500,
    "retry_count": 0,
    "success": true,
    "error_type": null,
    "trace_id": "abc123..." | null,
    "request_id": "..."
  }
}
```

El campo `metadata` es **aditivo** desde commit `2555269` (cierre del TODO #1
del frontend R1): los campos clínicos siguen al top-level, lo nuevo vive bajo
`metadata`. Schema canónico: `apps/api/src/sica_api/schemas.py::ExtractionMetadata`.

Usos típicos:
- **Frontend** persiste `provider_id`, `prompt_version`, `cost_usd`, `latency_ms`,
  `trace_id` en la fila `controles` de Supabase para auditoría longitudinal.
- **Operadores** correlacionan `trace_id` con el dashboard Langfuse
  (`https://us.cloud.langfuse.com/trace/<trace_id>`).
- **Pricing dashboards** suman `cost_usd` por médico/clínica.

Compat: los clientes que no leen `metadata` siguen funcionando sin cambio —
los campos del `ObstetricSummary` están en el mismo lugar de antes.

Shape del error `400` (provider inválido):

```json
{
  "error": "invalid_provider",
  "detail": "Provider 'openai' no es válido. Valores aceptados: ['anthropic', 'vertex'].",
  "provider": "openai",
  "request_id": "..."
}
```

Shape del error `503` (provider no disponible):

```json
{
  "error": "provider_unavailable",
  "detail": "Provider 'vertex' no disponible: VertexMedGemmaProvider.extract no está implementado. Pendiente sesión con GCP credentials (issue #12).",
  "provider": "vertex",
  "error_type": "NotImplementedError",
  "request_id": "...",
  "error_id": "..."
}
```

Política de fallback: **ninguno**. Si el provider seleccionado falla, el cliente recibe el error explícito y decide si reintentar con otro provider. Fallback silencioso oculta problemas operacionales — ver ADR 0004 § Actualización 2026-05-27.

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

# Con provider explícito (default si se omite):
curl -X POST "http://localhost:8000/extract?provider=anthropic" \
  -F "file=@../../services/clinical-extractor/data/synthetic_case_01.pdf"

# Provider stub — devuelve 503 hasta que GCP MedGemma esté configurado:
curl -X POST "http://localhost:8000/extract?provider=vertex" \
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

## Deployment

`sica-api` se deploya a **Render** como Python Web Service. Configuración declarativa en [`render.yaml`](../../render.yaml) (raíz del repo). Checklist exacto para la UI de Render en [`RENDER.md`](RENDER.md).

URL de producción (cuando esté desplegada): `https://sica-api.onrender.com`.

Resumen rápido:

```bash
# Render lee render.yaml. Build:
pip install --upgrade pip && pip install -e .

# Start:
uvicorn sica_api.main:app --host 0.0.0.0 --port $PORT
```

Health check: `/health` debe responder <100ms con `{ "status": "ok", ..., "timestamp": "..." }` para que Render no marque el servicio como unhealthy.

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
