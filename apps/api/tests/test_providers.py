"""Tests del endpoint GET /providers.

Cubren:
- Status code y shape de la respuesta.
- Provider anthropic con modelos Claude esperados.
- Provider vertex-medgemma con is_available=False y nota explicativa.
- Default provider id == "anthropic".
- Exactamente un modelo default por provider.
- Capabilities válidas (Literal).
- ``total_providers`` y ``available_count`` consistentes.
- /models legacy sigue funcionando — sanity check.
"""

from __future__ import annotations


def test_get_providers_returns_200(make_client):
    client = make_client()
    response = client.get("/providers")
    assert response.status_code == 200


def test_response_has_expected_fields(make_client):
    client = make_client()
    data = client.get("/providers").json()
    assert "providers" in data
    assert "default_provider_id" in data
    assert "total_providers" in data
    assert "available_count" in data
    assert isinstance(data["providers"], list)
    assert isinstance(data["total_providers"], int)
    assert isinstance(data["available_count"], int)


def test_includes_anthropic_provider(make_client):
    client = make_client()
    data = client.get("/providers").json()
    anthropic = next(
        (p for p in data["providers"] if p["provider_id"] == "anthropic"),
        None,
    )
    assert anthropic is not None, "esperaba provider 'anthropic' en la respuesta"
    model_ids = [m["id"] for m in anthropic["models"]]
    assert "claude-sonnet-4-5-20250929" in model_ids


def test_includes_vertex_medgemma_provider(make_client):
    client = make_client()
    data = client.get("/providers").json()
    medgemma = next(
        (p for p in data["providers"] if p["provider_id"] == "vertex-medgemma"),
        None,
    )
    assert medgemma is not None
    # Stub sin GCP creds: no debe estar disponible.
    assert medgemma["is_available"] is False
    assert medgemma["available_note"] is not None
    assert "issue #12" in medgemma["available_note"].lower() or "#12" in medgemma["available_note"]


def test_default_provider_is_anthropic(make_client):
    client = make_client()
    data = client.get("/providers").json()
    assert data["default_provider_id"] == "anthropic"


def test_each_provider_has_exactly_one_default_model(make_client):
    client = make_client()
    data = client.get("/providers").json()
    for provider in data["providers"]:
        defaults = [m for m in provider["models"] if m["is_default"]]
        assert len(defaults) == 1, (
            f"Provider {provider['provider_id']} debería tener exactamente "
            f"1 modelo default, tiene {len(defaults)}: {defaults}"
        )


def test_capabilities_are_valid(make_client):
    client = make_client()
    data = client.get("/providers").json()
    valid_caps = {"tool_use", "vision", "streaming", "long_context"}
    for provider in data["providers"]:
        for cap in provider["capabilities"]:
            assert cap in valid_caps, (
                f"Capability '{cap}' del provider {provider['provider_id']} no es válida"
            )


def test_total_providers_matches_array_length(make_client):
    client = make_client()
    data = client.get("/providers").json()
    assert data["total_providers"] == len(data["providers"])


def test_available_count_is_correct(make_client):
    client = make_client()
    data = client.get("/providers").json()
    actual_available = sum(1 for p in data["providers"] if p["is_available"])
    assert data["available_count"] == actual_available


def test_available_note_is_none_when_provider_available(make_client):
    """Si un provider está disponible, available_note debe ser None."""
    client = make_client()
    data = client.get("/providers").json()
    for provider in data["providers"]:
        if provider["is_available"]:
            assert provider["available_note"] is None, (
                f"Provider {provider['provider_id']} disponible pero con nota: "
                f"{provider['available_note']}"
            )


def test_anthropic_capabilities_include_tool_use(make_client):
    """Anthropic Claude soporta tool_use — debe aparecer en capabilities."""
    client = make_client()
    data = client.get("/providers").json()
    anthropic = next(p for p in data["providers"] if p["provider_id"] == "anthropic")
    assert "tool_use" in anthropic["capabilities"]


def test_models_endpoint_still_works(make_client):
    """Sanity check: NO romper /models existente.

    El frontend lo consume con shape ``list[ModelInfo]`` (no objeto envuelto).
    """
    client = make_client()
    response = client.get("/models")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list), "el shape de /models debe ser una lista plana"
    # Sanity: al menos los campos requeridos por el frontend.
    required = {"id", "provider", "type", "phi_allowed", "active", "role", "notes"}
    for item in data:
        assert required.issubset(item.keys()), f"missing fields en {item}"
