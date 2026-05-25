"""Tests para GET /health."""

from __future__ import annotations

import pytest

from sica_api import extractor_status


@pytest.fixture(autouse=True)
def _clear_extractor_module_cache():
    """``extractor_module_available`` cachea el resultado por proceso. Limpiamos
    antes y después de cada test para que los monkeypatches sean efectivos
    y no se filtren entre tests.
    """
    extractor_status._cached_check.cache_clear()
    yield
    extractor_status._cached_check.cache_clear()


def test_health_ok_when_api_key_and_module_present(make_client):
    """En CI clinical_extractor está instalado, así que con api_key debe ser True."""
    client = make_client(api_key="test-key")
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
    assert body["extractor_available"] is True
    # timestamp: formato UTC ISO 8601 con 'Z'
    assert isinstance(body["timestamp"], str)
    assert body["timestamp"].endswith("Z")
    assert "T" in body["timestamp"]


def test_health_responds_fast(make_client):
    """Render health checks corren cada 5-30s. <100ms es objetivo."""
    import time

    client = make_client(api_key="test-key")
    start = time.perf_counter()
    response = client.get("/health")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert response.status_code == 200
    # Margen amplio para CI lento; en local debería ser <10ms.
    assert elapsed_ms < 500, f"/health took {elapsed_ms:.0f}ms (>500ms)"


def test_health_extractor_unavailable_when_api_key_missing(make_client):
    client = make_client(api_key=None)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["extractor_available"] is False


def test_health_extractor_unavailable_when_module_missing(
    make_client, monkeypatch
):
    """Cuando el paquete clinical_extractor no se puede importar, debe reportar False.

    Simula el caso de producción que motivó este cambio: render.yaml no
    instalaba el extractor y /health mentía reportando True solo por la
    presencia del env var.
    """
    # Forzamos al cache a que devuelva False sin tocar el paquete real.
    monkeypatch.setattr(
        "sica_api.routes.health.extractor_module_available",
        lambda: False,
    )
    client = make_client(api_key="test-key")  # env var SÍ está
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["extractor_available"] is False, (
        "extractor_available debe ser False si el módulo no se puede importar, "
        "aunque ANTHROPIC_API_KEY esté presente"
    )


def test_health_extractor_unavailable_when_both_missing(make_client, monkeypatch):
    """Falla con AND lógico: ambas condiciones deben ser True para reportar True."""
    monkeypatch.setattr(
        "sica_api.routes.health.extractor_module_available",
        lambda: False,
    )
    client = make_client(api_key=None)
    response = client.get("/health")
    body = response.json()
    assert body["extractor_available"] is False


def test_health_propagates_request_id(make_client):
    client = make_client()
    response = client.get("/health", headers={"X-Request-ID": "test-fixed-id-123"})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "test-fixed-id-123"


def test_health_generates_request_id_when_missing(make_client):
    client = make_client()
    response = client.get("/health")
    assert response.status_code == 200
    rid = response.headers.get("X-Request-ID")
    assert rid is not None and len(rid) >= 8
