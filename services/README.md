# services/

Servicios Python. Cada subcarpeta es un servicio independiente con su propio `pyproject.toml`, `.venv`, dependencies y tests.

## Servicios actuales

| Servicio | Estado | Descripción |
|---|---|---|
| `clinical-extractor` | R0 — en desarrollo | Pipeline PDF → JSON clínico estructurado (Pydantic). Primera capa de la Multimodal Ingestion Layer (STRATEGY § 6.3). |

## Convenciones

- Una carpeta por servicio: `services/<nombre>/`.
- Cada servicio tiene `pyproject.toml` (no `setup.py`), `src/<package_name>/` layout, tests en `tests/`.
- Python `>=3.13`.
- Dependencias se manejan con `pip` o `uv` dentro del `.venv` local de cada servicio — no hay workspace Python compartido por ahora.
- Lint: `ruff check`. Type check: `mypy`.
