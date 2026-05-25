"""Tests para GET /models."""

from __future__ import annotations


def test_models_returns_list(make_client):
    client = make_client()
    response = client.get("/models")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) >= 5


def test_models_each_item_has_required_fields(make_client):
    client = make_client()
    body = client.get("/models").json()
    required = {"id", "provider", "type", "phi_allowed", "active", "role", "notes"}
    for item in body:
        assert required.issubset(item.keys()), f"missing fields in {item}"


def test_models_claude_is_dev_only_in_r0(make_client):
    """ADR 0003/0004: Claude está vetado para PHI real en Fase 1."""
    client = make_client()
    body = client.get("/models").json()
    claude = next(
        (m for m in body if m["id"].startswith("claude-")),
        None,
    )
    assert claude is not None
    assert claude["phi_allowed"] is False
    assert claude["role"] == "dev_only"


def test_models_medgemma_is_default_but_inactive_in_r0(make_client):
    """MedGemma 4B es el default planificado pero no activo hasta cierre de #12."""
    client = make_client()
    body = client.get("/models").json()
    medgemma = next(
        (m for m in body if m["id"].startswith("medgemma-4b")),
        None,
    )
    assert medgemma is not None
    assert medgemma["role"] == "default"
    assert medgemma["phi_allowed"] is True
    assert medgemma["active"] is False


def test_models_includes_runtime_availability(make_client):
    """Bloque E: cada item debe traer is_available + provider_id (puede ser None)."""
    client = make_client()
    body = client.get("/models").json()
    for item in body:
        assert "is_available" in item
        assert "provider_id" in item
        assert isinstance(item["is_available"], bool)
        # provider_id es string o None
        assert item["provider_id"] is None or isinstance(item["provider_id"], str)


def test_models_claude_models_have_anthropic_provider(make_client):
    """Bloque E: los modelos Claude deben mapear al provider 'anthropic'."""
    client = make_client()
    body = client.get("/models").json()
    claudes = [m for m in body if m["id"].startswith("claude-")]
    assert claudes, "esperaba al menos un modelo Claude"
    for m in claudes:
        assert m["provider_id"] == "anthropic"


def test_models_medgemma_4b_maps_to_vertex_provider(make_client):
    """Bloque E: medgemma-4b-it debe mapear al provider 'vertex-medgemma' (stub)."""
    client = make_client()
    body = client.get("/models").json()
    medgemma = next(
        (m for m in body if m["id"] == "medgemma-4b-it"),
        None,
    )
    assert medgemma is not None
    assert medgemma["provider_id"] == "vertex-medgemma"
    # Stub no implementado — is_available siempre False
    assert medgemma["is_available"] is False
