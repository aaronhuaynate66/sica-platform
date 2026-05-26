"""Shared pytest fixtures."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from sica_api.main import create_app
from sica_api.routes.extract import get_extractor
from sica_api.settings import Settings, get_settings


def _build_settings(*, api_key: str | None = "test-key", max_mb: int = 10) -> Settings:
    s = Settings(
        anthropic_api_key=api_key,
        max_file_size_mb=max_mb,
        allowed_origins=["http://localhost:3000"],
        log_level="INFO",
    )
    return s


@pytest.fixture
def make_client():
    """Builder: configures settings + extractor override per test."""

    created: list[TestClient] = []

    def _make(
        *,
        api_key: str | None = "test-key",
        max_mb: int = 10,
        extractor=None,
    ) -> TestClient:
        # Important: re-create the app per test so middleware + overrides
        # apply cleanly.
        app = create_app()
        app.dependency_overrides[get_settings] = lambda: _build_settings(
            api_key=api_key, max_mb=max_mb
        )
        if extractor is not None:
            app.dependency_overrides[get_extractor] = lambda: extractor
        client = TestClient(app)
        created.append(client)
        return client

    yield _make
    for c in created:
        c.close()


@pytest.fixture
def fake_extractor():
    """Returns a callable that mimics the clinical-extractor contract.

    ``**_kwargs`` swallow garantiza compat con cualquier kwarg que el
    handler agregue en el futuro (p. ej. ``parent_trace_id``,
    ``parent_span_id`` introducidos por el tracing jerárquico).
    """

    def _fake(pdf_path, *, api_key: str, **_kwargs: Any) -> dict[str, Any]:
        return {
            "patient_age": 32,
            "gestational_age_weeks": 28.3,
            "fum": "2025-09-15",
            "fpp": "2026-06-22",
            "active_problems": ["Anemia leve gestacional"],
            "risk_factors": ["Cesárea previa"],
            "lab_results": [],
            "notes_summary": "Caso de prueba.",
            "confidence_score": 0.91,
            "evidence_spans": [],
        }

    return _fake


@pytest.fixture
def failing_extractor():
    """Extractor that always raises — exercises the 500 path."""

    def _boom(pdf_path, *, api_key: str, **_kwargs: Any):
        raise RuntimeError("simulated extractor failure")

    return _boom


@pytest.fixture(autouse=True)
def _disable_langfuse_in_tests(monkeypatch):
    """Aísla TODOS los tests de Langfuse Cloud.

    Igual que en clinical-extractor, los tests del API que ejercen
    ``POST /extract`` con un fake extractor invocan internamente
    ``start_extract_trace``. Si el entorno tiene LANGFUSE_* presentes
    (CI o local con .env del clinical-extractor cargado al sys), los
    tests mandarían traces reales con datos sintéticos al dashboard.

    Solución defensiva: en cada test borramos las env vars y limpiamos
    el cache del cliente. Tests que quieran simular Langfuse habilitado
    deben usar ``monkeypatch.setenv`` + patching del SDK explícitamente.
    """
    for var in (
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_BASE_URL",
        "LANGFUSE_TRACING_ENVIRONMENT",
    ):
        monkeypatch.delenv(var, raising=False)
    # Limpiar cache del cliente (también del settings global) si ya
    # fue inicializado por un test anterior.
    from sica_api import tracing as _tracing
    from sica_api.settings import get_settings as _get_settings

    _tracing.get_langfuse_client.cache_clear()
    _get_settings.cache_clear()
    yield
    _tracing.get_langfuse_client.cache_clear()
    _get_settings.cache_clear()


@pytest.fixture
def minimal_pdf_bytes() -> bytes:
    """A tiny but valid-ish PDF (magic bytes + EOF marker).

    The fake_extractor doesn't actually parse it, so we don't need a real
    PDF payload — just bytes that pass the `%PDF-` magic-bytes check.
    """
    return b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
