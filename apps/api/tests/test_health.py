"""Tests para GET /health."""

from __future__ import annotations


def test_health_ok_when_api_key_present(make_client):
    client = make_client(api_key="test-key")
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "status": "ok",
        "version": "0.1.0",
        "extractor_available": True,
    }


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
