# clinical-extractor

Servicio Python de SICA. **Extrae historias clínicas obstétricas desde PDFs nativos hacia objetos Pydantic validados con evidencia trazable.**

Primera capa concreta de la **Multimodal Ingestion Layer** (STRATEGY § 6.3). Es uno de los entregables del release **R0 Foundation** (`docs/roadmap.md` § R0).

## Qué hace

```
PDF nativo  ─┐
             ├─→  pypdf (texto plano)  ─→  Claude (tool use)  ─→  ObstetricSummary (Pydantic)
prompt v0.1 ─┘
```

Salida estructurada:

- `patient_age`, `gestational_age_weeks`, `fum`, `fpp`
- `active_problems[]`, `risk_factors[]`
- `lab_results[]` (con `LabResult`: name, value, unit, date, abnormal)
- `notes_summary`
- `confidence_score` (0.0–1.0)
- `evidence_spans[]` (cada hecho trazado a `(source_page, source_text)` verbatim)

## Principios de diseño

1. **Abstención > alucinación.** Si el campo no está en el documento, devuelve `None` / `[]`. NO se completa con inferencia general.
2. **Evidencia trazable.** Cada hecho no trivial debe poder rastrearse a un span del documento fuente.
3. **Confianza calibrada.** `confidence_score` refleja honestamente cuán claro estaba el documento.
4. **Prompts versionados.** Ningún cambio de prompt entra sin bump de versión + corrida de evals.
5. **Sin PII.** Nombres, DNI, identificadores no entran al output.

## Instalación

Requiere Python 3.13+.

```bash
cd services/clinical-extractor

# Crear y activar virtualenv
python -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows PowerShell:
.venv\Scripts\Activate.ps1

# Instalar el paquete + dependencias de desarrollo
pip install -e ".[dev]"
```

## Configuración

```bash
cp .env.example .env
```

Luego edita `.env` y completa al menos `ANTHROPIC_API_KEY`. **NUNCA commitees `.env`** (está en `.gitignore`).

Variables soportadas:

| Variable | Default | Propósito |
|---|---|---|
| `ANTHROPIC_API_KEY` | — (obligatorio) | API key de Anthropic. |
| `CLAUDE_MODEL` | `claude-sonnet-4-5-20250929` | Modelo a usar. |
| `CLAUDE_MAX_TOKENS` | `4096` | Tope de tokens de salida. |
| `CLAUDE_TIMEOUT_SECONDS` | `60` | Timeout total por request al modelo. |
| `CLAUDE_MAX_RETRIES` | `3` | Reintentos en errores transitorios (red, 429, 5xx). |
| `CLAUDE_INITIAL_BACKOFF` | `1.0` | Backoff inicial en segundos antes del primer reintento. |
| `CLAUDE_MAX_BACKOFF` | `16.0` | Tope del backoff exponencial. |
| `DEBUG_RAW_OUTPUT` | `false` | Si true, dumpea también el JSON crudo del modelo. |

## Uso

### CLI

```bash
# Extrae a stdout
clinical-extractor extract data/synthetic_case_01.pdf

# A archivo
clinical-extractor extract data/synthetic_case_01.pdf -o out.json

# Override de modelo
clinical-extractor extract data/synthetic_case_01.pdf --model claude-sonnet-4-5-20250929
```

Equivalente sin instalar como script:

```bash
python -m clinical_extractor.cli extract data/synthetic_case_01.pdf
```

### Batch processing

Procesa todos los PDFs de un directorio en paralelo limitado:

```bash
# Default: concurrency=3, output JSONs al mismo directorio
clinical-extractor extract-batch data/

# Concurrency custom + output_dir separado + glob específico
clinical-extractor extract-batch data/ \
  --output-dir batch-out/ \
  --concurrency 2 \
  --pattern "synthetic_case_0[2-7]*.pdf"
```

Por cada `foo.pdf` produce `foo.json` con el `ObstetricSummary` extraído. Al final imprime un resumen con cuántos procesados, exitosos, fallidos y tiempo total. Salida en código distinto de 0 si **algún** PDF falló — los exitosos se guardan igual.

Concurrency está acotada a `[1, 8]`. El default 3 está dimensionado para no saturar el rate limit estándar de Anthropic.

## Production readiness

El extractor tiene los siguientes mecanismos en R0:

### Retry con backoff exponencial

Reintenta automáticamente en errores transitorios:

- `anthropic.APIConnectionError` (red)
- `anthropic.APITimeoutError`
- `anthropic.RateLimitError` (429)
- `anthropic.InternalServerError` (5xx)

**NO** reintenta en errores del cliente (sería esfuerzo perdido y/o billable):

- `anthropic.BadRequestError` (400)
- `anthropic.AuthenticationError` (401)
- `anthropic.PermissionDeniedError` (403)
- `anthropic.NotFoundError` (404)
- `anthropic.UnprocessableEntityError` (422)

Política default: 3 reintentos, backoff exponencial 1s → 2s → 4s → 8s → 16s cap, jitter ±20% para evitar thundering herd. Override vía `CLAUDE_MAX_RETRIES`, `CLAUDE_INITIAL_BACKOFF`, `CLAUDE_MAX_BACKOFF` o argumentos a `extract_from_pdf`.

### Timeout

`CLAUDE_TIMEOUT_SECONDS` (default 60s) se pasa al cliente Anthropic. Aplica por request — un retry empieza con timeout fresco.

### Telemetría JSON-line

Cada extracción emite **un único registro** al logger `clinical_extractor.telemetry`. La CLI lo conecta a stderr con formato JSON-line:

```json
{
  "error_type": null,
  "latency_ms": 1840,
  "model_used": "claude-sonnet-4-5-20250929",
  "operation_id": "8c2a3f4e-1234-...",
  "pages_extracted": 2,
  "pdf_path": "data/synthetic_case_01.pdf",
  "pdf_size_bytes": 5626,
  "prompt_version": "0.1.0",
  "retry_count": 0,
  "success": true,
  "timestamp": "2026-05-22T05:30:00Z",
  "token_usage": {"input_tokens": 1234, "output_tokens": 567}
}
```

**Garantías** (verificadas por tests):

- Una línea JSON válida por extracción (incluso si la extracción falla).
- **Cero contenido del PDF** y **cero contenido del output** — solo metadatos. El payload de PHI nunca cruza al log.
- Coherente con ADR 0004 Nivel 4 (es un subset operacional del audit trail completo).

Interpretación de campos:

| Campo | Significado |
|---|---|
| `success` | `true` si la extracción terminó con un `ObstetricSummary` válido. |
| `error_type` | Clase Python de la excepción si falló (`AuthenticationError`, `ExtractionError`, etc.). |
| `retry_count` | Cuántos reintentos consumió (0 en happy path). |
| `latency_ms` | Tiempo end-to-end de `extract_from_pdf` (incluye PDF read + retries + validación). |
| `token_usage` | `input_tokens` + `output_tokens` reportados por la API. `null` si la API no los devolvió. |

Como librería, configurar el handler propio:

```python
from clinical_extractor import telemetry
telemetry.configure_stream_handler(stream=sys.stderr)
# o conectar un handler propio (CloudWatch, Loki, archivo rotativo, etc.)
```

### Como librería

```python
from pathlib import Path
from clinical_extractor import extract_from_pdf

summary = extract_from_pdf(Path("data/synthetic_case_01.pdf"))
print(summary.model_dump_json(indent=2))
print(f"Confianza: {summary.confidence_score:.2f}")
```

## Testing

```bash
# Tests unitarios (sin red, sin API key)
pytest

# Con cobertura
pytest --cov=clinical_extractor --cov-report=term-missing

# Lint + format check
ruff check .
ruff format --check .

# Type check
mypy src
```

## Estructura

```
clinical-extractor/
├── pyproject.toml                 ← config moderna (PEP 621 + hatchling)
├── README.md                      ← este archivo
├── .env.example                   ← template de variables (sin valores reales)
├── src/
│   └── clinical_extractor/
│       ├── __init__.py            ← exports públicos
│       ├── cli.py                 ← entry point Click
│       ├── extractor.py           ← lógica core PDF → ObstetricSummary
│       ├── prompts.py             ← prompts versionados (registry)
│       └── schemas.py             ← Pydantic models
├── tests/
│   └── test_extractor.py          ← unit tests (sin red)
└── data/
    └── synthetic_case_01.pdf      ← PDF sintético marcado, solo para pruebas
```

## Datos

**Solo PDFs sintéticos marcados** entran a `data/`. El `.gitignore` raíz bloquea `*.pdf` por defecto y solo abre excepciones nominales explícitas (ver raíz del repo).

**NUNCA poner PHI real aquí.** Si necesitás validar contra una historia real, hacelo en un directorio fuera del repo o en almacenamiento clínico del partner.

## Limitaciones conocidas (R0)

- **PDFs escaneados sin capa de texto** devuelven `ExtractionError`. El routing a OCR (Document AI o Tesseract local) sale en R1.
- **No persiste** los resultados ni audit trail aún. Audit trail completo (ADR 0004 Nivel 4) entra con el orquestador en R1. La telemetría actual es un subset operacional, no audit log regulatorio.
- **Costos no agregados**. `token_usage` por operación está disponible vía telemetría; la agregación en dashboards entra con Langfuse en issue #14.

## Referencias

- STRATEGY.md § 6.3 — Multimodal Ingestion Layer
- STRATEGY.md § 10 — AI Evaluation Infrastructure
- STRATEGY.md § 11.4 — Política de routing de modelos
- docs/roadmap.md § R0 — entregables y gate de salida
- docs/decisions/0001-monorepo-turborepo.md — por qué este servicio vive en monorepo
