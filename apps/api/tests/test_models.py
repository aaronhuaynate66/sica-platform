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
    medgemma = next((m for m in body if m["id"] == "medgemma-4b"), None)
    assert medgemma is not None
    assert medgemma["role"] == "default"
    assert medgemma["phi_allowed"] is True
    assert medgemma["active"] is False
