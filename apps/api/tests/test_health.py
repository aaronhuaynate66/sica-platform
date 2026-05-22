"""Tests para GET /health."""

from __future__ import annotations


def test_health_ok_when_api_key_present(make_client):
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
