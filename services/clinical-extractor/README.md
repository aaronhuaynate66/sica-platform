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
| `CLAUDE_TIMEOUT_SECONDS` | `60` | Timeout de la llamada al modelo. |
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
- **Sin retries automáticos** ante errores transitorios del modelo. Si la llamada falla, el CLI sale con código 1 — habrá que reintentar manualmente.
- **No persiste** los resultados ni audit trail aún. Esa capa entra cuando arranca el harness de evals (R0 mid).
- **Costos no medidos**. El consumo por extracción se mide a partir del primer corrido con Langfuse en R0 mid.

## Referencias

- STRATEGY.md § 6.3 — Multimodal Ingestion Layer
- STRATEGY.md § 10 — AI Evaluation Infrastructure
- STRATEGY.md § 11.4 — Política de routing de modelos
- docs/roadmap.md § R0 — entregables y gate de salida
- docs/decisions/0001-monorepo-turborepo.md — por qué este servicio vive en monorepo
