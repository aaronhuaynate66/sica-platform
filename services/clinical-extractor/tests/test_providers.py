"""Tests del adapter pattern multi-provider (Bloque E, R0).

Cubre:
- ``ProviderRegistry`` — register, get, get_for_model, list_available.
- ``AnthropicProvider`` — provider_id, supported_models, is_available,
  extract con mock del cliente, retry policy, errores no-retriables.
- ``VertexMedGemmaProvider`` — provider_id, is_available siempre False en
  el stub, extract levanta NotImplementedError.

No consume API real — todo mockeado.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import anthropic
import httpx
import pytest

from clinical_extractor.prompts import get_active_prompt
from clinical_extractor.providers import (
    AnthropicProvider,
    ExtractionRequest,
    LLMProvider,
    ProviderNotAvailableError,
    ProviderRegistry,
    VertexMedGemmaProvider,
)
from clinical_extractor.providers.anthropic_provider import (
    AnthropicExtractionError,
)

# =========================================================================
# Helpers — reproducen mocks de test_hardening.py para mantener consistencia
# =========================================================================


def _mock_anthropic_response(payload: dict) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = "record_obstetric_summary"
    block.input = payload
    response = MagicMock()
    response.content = [block]
    response.stop_reason = "tool_use"
    response.usage = MagicMock(input_tokens=200, output_tokens=80)
    return response


def _valid_payload() -> dict:
    return {
        "confidence_score": 0.9,
        "active_problems": [],
        "risk_factors": [],
        "lab_results": [],
        "evidence_spans": [],
        "notes_summary": "Test.",
        "patient_age": 30,
        "gestational_age_weeks": 25.0,
    }


def _make_request(model_id: str = "claude-sonnet-4-5-20250929") -> ExtractionRequest:
    return ExtractionRequest(
        document_text="Historia clínica obstétrica de prueba.",
        prompt=get_active_prompt(),
        model_id=model_id,
        max_retries=2,
        initial_backoff=0.001,
        max_backoff=0.001,
    )


def _make_connection_error() -> anthropic.APIConnectionError:
    return anthropic.APIConnectionError(
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
    )


def _make_auth_error() -> anthropic.AuthenticationError:
    body = b'{"error":{"type":"authentication_error","message":"invalid x-api-key"}}'
    response = httpx.Response(
        status_code=401,
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
        content=body,
        headers={"content-type": "application/json"},
    )
    return anthropic.AuthenticationError(
        message="invalid x-api-key",
        response=response,
        body=json.loads(body),
    )


# =========================================================================
# ProviderRegistry
# =========================================================================


class _FakeProvider(LLMProvider):
    """Provider de prueba — declara modelos arbitrarios para testear registry."""

    def __init__(
        self,
        provider_id: str,
        models: tuple[str, ...],
        *,
        available: bool = True,
    ) -> None:
        self._pid = provider_id
        self._models = models
        self._available = available

    @property
    def provider_id(self) -> str:
        return self._pid

    @property
    def supported_models(self) -> list[str]:
        return list(self._models)

    def is_available(self) -> bool:
        return self._available

    def extract(self, request):  # type: ignore[no-untyped-def]
        raise NotImplementedError


class TestProviderRegistry:
    def test_register_adds_provider(self) -> None:
        reg = ProviderRegistry(register_defaults=False)
        p = _FakeProvider("fake", ("model-x",))
        reg.register(p)
        assert reg.get("fake") is p

    def test_register_replaces_existing_by_id(self) -> None:
        reg = ProviderRegistry(register_defaults=False)
        p1 = _FakeProvider("fake", ("v1",))
        p2 = _FakeProvider("fake", ("v2",))
        reg.register(p1)
        reg.register(p2)
        assert reg.get("fake") is p2

    def test_get_raises_value_error_if_not_registered(self) -> None:
        reg = ProviderRegistry(register_defaults=False)
        with pytest.raises(ValueError, match="no registrado"):
            reg.get("nonexistent")

    def test_get_for_model_finds_supporting_provider(self) -> None:
        reg = ProviderRegistry(register_defaults=False)
        reg.register(_FakeProvider("alpha", ("model-a", "model-b")))
        reg.register(_FakeProvider("beta", ("model-c",)))
        assert reg.get_for_model("model-b").provider_id == "alpha"
        assert reg.get_for_model("model-c").provider_id == "beta"

    def test_get_for_model_returns_none_when_unsupported(self) -> None:
        reg = ProviderRegistry(register_defaults=False)
        reg.register(_FakeProvider("alpha", ("model-a",)))
        assert reg.get_for_model("model-zzz") is None

    def test_list_available_filters_unavailable(self) -> None:
        reg = ProviderRegistry(register_defaults=False)
        reg.register(_FakeProvider("up", ("m1",), available=True))
        reg.register(_FakeProvider("down", ("m2",), available=False))
        avail = reg.list_available()
        assert [p.provider_id for p in avail] == ["up"]

    def test_default_registry_has_anthropic_and_medgemma(self) -> None:
        reg = ProviderRegistry()
        ids = [p.provider_id for p in reg.list_all()]
        assert "anthropic" in ids
        assert "vertex-medgemma" in ids


# =========================================================================
# AnthropicProvider
# =========================================================================


class TestAnthropicProvider:
    def test_provider_id_is_anthropic(self) -> None:
        assert AnthropicProvider().provider_id == "anthropic"

    def test_supported_models_includes_sonnet_opus_haiku(self) -> None:
        models = AnthropicProvider().supported_models
        assert "claude-sonnet-4-5-20250929" in models
        assert "claude-opus-4-7" in models
        assert "claude-haiku-4-5-20251001" in models

    def test_is_available_true_with_env_var(self, monkeypatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-x")
        assert AnthropicProvider().is_available() is True

    def test_is_available_false_without_env_var(self, monkeypatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert AnthropicProvider().is_available() is False

    def test_is_available_true_with_injected_client(self) -> None:
        provider = AnthropicProvider(client=MagicMock())
        assert provider.is_available() is True

    def test_extract_success_returns_extraction_response(self) -> None:
        client = MagicMock()
        client.messages.create.return_value = _mock_anthropic_response(_valid_payload())
        provider = AnthropicProvider(client=client)

        response = provider.extract(_make_request())

        assert response.parsed_output["confidence_score"] == 0.9
        assert response.input_tokens == 200
        assert response.output_tokens == 80
        assert response.model_used == "claude-sonnet-4-5-20250929"
        assert response.finish_reason == "tool_use"
        assert response.retry_count == 0
        assert response.latency_ms >= 0
        client.messages.create.assert_called_once()

    def test_extract_unsupported_model_raises_value_error(self) -> None:
        provider = AnthropicProvider(client=MagicMock())
        with pytest.raises(ValueError, match="no soporta"):
            provider.extract(_make_request(model_id="gpt-4o"))

    def test_extract_retries_on_connection_error(self) -> None:
        client = MagicMock()
        client.messages.create.side_effect = [
            _make_connection_error(),
            _make_connection_error(),
            _mock_anthropic_response(_valid_payload()),
        ]
        provider = AnthropicProvider(client=client)
        response = provider.extract(_make_request())
        assert response.retry_count == 2
        assert client.messages.create.call_count == 3

    def test_extract_does_not_retry_on_auth_error(self) -> None:
        client = MagicMock()
        client.messages.create.side_effect = _make_auth_error()
        provider = AnthropicProvider(client=client)
        with pytest.raises(anthropic.AuthenticationError):
            provider.extract(_make_request())
        assert client.messages.create.call_count == 1

    def test_extract_exhausts_retries_then_raises(self) -> None:
        client = MagicMock()
        client.messages.create.side_effect = _make_connection_error()
        provider = AnthropicProvider(client=client)
        with pytest.raises(AnthropicExtractionError, match="Reintentos agotados"):
            provider.extract(_make_request())

    def test_extract_raises_provider_not_available_without_key(
        self, monkeypatch
    ) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        provider = AnthropicProvider()  # no client inyectado
        with pytest.raises(ProviderNotAvailableError, match="ANTHROPIC_API_KEY"):
            provider.extract(_make_request())


# =========================================================================
# VertexMedGemmaProvider
# =========================================================================


class TestVertexMedGemmaProvider:
    def test_provider_id_is_vertex_medgemma(self) -> None:
        assert VertexMedGemmaProvider().provider_id == "vertex-medgemma"

    def test_supported_models_includes_medgemma_4b_it(self) -> None:
        assert "medgemma-4b-it" in VertexMedGemmaProvider().supported_models

    def test_is_available_returns_false_in_stub(self, monkeypatch) -> None:
        # Aun con env vars completas, el stub responde False — porque extract
        # no está implementado todavía.
        for v in ("GOOGLE_APPLICATION_CREDENTIALS", "GCP_PROJECT", "MEDGEMMA_ENDPOINT_ID"):
            monkeypatch.setenv(v, "dummy")
        assert VertexMedGemmaProvider().is_available() is False

    def test_is_available_returns_false_without_env_vars(self, monkeypatch) -> None:
        for v in ("GOOGLE_APPLICATION_CREDENTIALS", "GCP_PROJECT", "MEDGEMMA_ENDPOINT_ID"):
            monkeypatch.delenv(v, raising=False)
        assert VertexMedGemmaProvider().is_available() is False

    def test_extract_raises_not_implemented_error(self) -> None:
        provider = VertexMedGemmaProvider()
        with pytest.raises(NotImplementedError, match="issue #12"):
            provider.extract(_make_request(model_id="medgemma-4b-it"))
