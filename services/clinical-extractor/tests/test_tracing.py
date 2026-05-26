"""Tests de ``clinical_extractor.tracing``.

Cubren:

- ``get_langfuse_client()`` retorna ``None`` cuando las env vars no están.
- ``get_langfuse_client()`` retorna instancia cuando las env vars están
  (con Langfuse SDK mockeado).
- ``trace_extraction()`` es no-op cuando el cliente es ``None``.
- ``trace_extraction()`` llama ``start_observation`` con los args correctos.
- ``trace_extraction()`` jamás levanta cuando el SDK lanza.
- ``trace_extraction()`` computa ``cost_details`` correctamente.
- ``AnthropicProvider`` llama ``trace_extraction`` en path exitoso.
- ``AnthropicProvider`` llama ``trace_extraction`` con ``error=...`` antes de re-raise.

No llamamos a Langfuse real. Todo mockeado.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import anthropic
import httpx
import pytest

from clinical_extractor import tracing
from clinical_extractor.prompts import get_active_prompt
from clinical_extractor.providers import (
    AnthropicProvider,
    ExtractionRequest,
)
from clinical_extractor.providers.anthropic_provider import AnthropicExtractionError
from clinical_extractor.settings import LangfuseSettings

# Nota: la fixture autouse _isolate_tracing_env vive en tests/conftest.py
# y aísla TODOS los tests del .env real + limpia caches. No re-implementarla
# acá. Los helpers _patch_settings_enabled de abajo setean vars con monkeypatch
# que prevalecen sobre el delenv del conftest (lo cual es lo que queremos:
# tests de tracing pueden simular "Langfuse habilitado" caso por caso).


# =========================================================================
# Helpers de mock
# =========================================================================


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


def _make_request(
    case_id: str | None = "test_case_01",
    model_id: str = "claude-sonnet-4-5-20250929",
) -> ExtractionRequest:
    return ExtractionRequest(
        document_text="Historia clínica de prueba.",
        prompt=get_active_prompt(),
        model_id=model_id,
        max_retries=2,
        initial_backoff=0.001,
        max_backoff=0.001,
        case_id=case_id,
    )


def _make_connection_error() -> anthropic.APIConnectionError:
    return anthropic.APIConnectionError(
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
    )


def _patch_settings_enabled(monkeypatch, enabled: bool) -> None:
    """Forza LangfuseSettings.enabled al valor deseado vía env vars."""
    if enabled:
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
        monkeypatch.setenv("LANGFUSE_BASE_URL", "https://test.langfuse.local")
    else:
        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    # Importante: limpiar cache de settings y client.
    from clinical_extractor.settings import get_langfuse_settings

    get_langfuse_settings.cache_clear()
    tracing.get_langfuse_client.cache_clear()


# =========================================================================
# Settings — sanity
# =========================================================================


class TestLangfuseSettings:
    def test_enabled_false_when_keys_missing(self, monkeypatch) -> None:
        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
        settings = LangfuseSettings()
        assert settings.enabled is False

    def test_enabled_true_when_keys_present(self, monkeypatch) -> None:
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-x")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-x")
        settings = LangfuseSettings()
        assert settings.enabled is True

    def test_default_base_url_is_us_cloud(self, monkeypatch) -> None:
        monkeypatch.delenv("LANGFUSE_BASE_URL", raising=False)
        settings = LangfuseSettings()
        assert settings.base_url == "https://us.cloud.langfuse.com"

    def test_environment_defaults_to_development(self, monkeypatch) -> None:
        """Default fail-safe: sin env var explícita, traces caen en 'development'.

        Sin esto, smoke tests locales contaminan el dashboard 'production'
        (ver ADR 0007 § actualización 2026-05-26).
        """
        monkeypatch.delenv("LANGFUSE_TRACING_ENVIRONMENT", raising=False)
        settings = LangfuseSettings()
        assert settings.tracing_environment == "development"

    def test_environment_can_be_overridden_to_production(self, monkeypatch) -> None:
        """Render production setea LANGFUSE_TRACING_ENVIRONMENT=production via env var."""
        monkeypatch.setenv("LANGFUSE_TRACING_ENVIRONMENT", "production")
        settings = LangfuseSettings()
        assert settings.tracing_environment == "production"


# =========================================================================
# get_langfuse_client
# =========================================================================


class TestGetLangfuseClient:
    def test_returns_none_when_env_missing(self, monkeypatch) -> None:
        _patch_settings_enabled(monkeypatch, False)
        assert tracing.get_langfuse_client() is None

    def test_returns_instance_when_env_present(self, monkeypatch) -> None:
        _patch_settings_enabled(monkeypatch, True)
        with patch("langfuse.Langfuse") as mock_langfuse_cls:
            mock_instance = MagicMock()
            mock_langfuse_cls.return_value = mock_instance
            client = tracing.get_langfuse_client()
        assert client is mock_instance
        # Verificar que pasamos las credenciales correctamente.
        mock_langfuse_cls.assert_called_once()
        call_kwargs = mock_langfuse_cls.call_args.kwargs
        assert call_kwargs["public_key"] == "pk-lf-test"
        assert call_kwargs["secret_key"] == "sk-lf-test"
        assert call_kwargs["host"] == "https://test.langfuse.local"

    def test_returns_none_when_sdk_import_fails(self, monkeypatch) -> None:
        _patch_settings_enabled(monkeypatch, True)
        # Simular ImportError forzando un raise en la import diferida.
        with patch("langfuse.Langfuse", side_effect=RuntimeError("boom")):
            client = tracing.get_langfuse_client()
        assert client is None  # graceful fallback


# =========================================================================
# trace_extraction
# =========================================================================


class TestTraceExtraction:
    def test_noop_when_client_is_none(self, monkeypatch) -> None:
        _patch_settings_enabled(monkeypatch, False)
        # No debe lanzar.
        tracing.trace_extraction(
            case_id="x",
            model="claude-sonnet-4-5-20250929",
            provider_id="anthropic",
            input_tokens=100,
            output_tokens=50,
        )

    def test_calls_start_observation_with_correct_args(self, monkeypatch) -> None:
        _patch_settings_enabled(monkeypatch, True)
        mock_client = MagicMock()
        mock_generation = MagicMock()
        mock_client.start_observation.return_value = mock_generation

        with patch("langfuse.Langfuse", return_value=mock_client):
            tracing.trace_extraction(
                case_id="case_abc",
                model="claude-sonnet-4-5-20250929",
                provider_id="anthropic",
                input_tokens=1000,
                output_tokens=500,
                latency_ms=1500.0,
                output_json={"k": "v"},
            )

        mock_client.start_observation.assert_called_once()
        call_kwargs = mock_client.start_observation.call_args.kwargs
        assert call_kwargs["name"] == "extract_case_abc"
        assert call_kwargs["as_type"] == "generation"
        assert call_kwargs["model"] == "claude-sonnet-4-5-20250929"
        assert call_kwargs["output"] == {"k": "v"}
        assert call_kwargs["usage_details"]["input"] == 1000
        assert call_kwargs["usage_details"]["output"] == 500
        # 1000 input + 500 output sonnet: 0.003 + 0.0075 = 0.0105
        assert call_kwargs["cost_details"]["total"] == pytest.approx(0.0105, abs=1e-6)
        assert call_kwargs["level"] == "DEFAULT"
        # metadata canonica.
        assert call_kwargs["metadata"]["case_id"] == "case_abc"
        assert call_kwargs["metadata"]["provider_id"] == "anthropic"
        assert call_kwargs["metadata"]["latency_ms"] == 1500.0
        mock_generation.end.assert_called_once()

    def test_silent_when_sdk_raises(self, monkeypatch) -> None:
        _patch_settings_enabled(monkeypatch, True)
        mock_client = MagicMock()
        mock_client.start_observation.side_effect = RuntimeError("Langfuse cae")

        with patch("langfuse.Langfuse", return_value=mock_client):
            # No debe re-raise.
            tracing.trace_extraction(
                case_id="x",
                model="claude-sonnet-4-5-20250929",
                provider_id="anthropic",
                input_tokens=10,
                output_tokens=5,
            )

    def test_trace_without_parent_id_creates_top_level(self, monkeypatch) -> None:
        """Sin parent_trace_id, no se pasa trace_context al SDK (trace top-level)."""
        _patch_settings_enabled(monkeypatch, True)
        mock_client = MagicMock()
        mock_client.start_observation.return_value = MagicMock()
        with patch("langfuse.Langfuse", return_value=mock_client):
            tracing.trace_extraction(
                case_id="x",
                model="claude-sonnet-4-5-20250929",
                provider_id="anthropic",
                input_tokens=10,
                output_tokens=5,
            )
        call_kwargs = mock_client.start_observation.call_args.kwargs
        assert call_kwargs.get("trace_context") is None

    def test_trace_with_parent_id_creates_child(self, monkeypatch) -> None:
        """Con parent_trace_id, el observation se crea con trace_context."""
        _patch_settings_enabled(monkeypatch, True)
        mock_client = MagicMock()
        mock_client.start_observation.return_value = MagicMock()
        with patch("langfuse.Langfuse", return_value=mock_client):
            tracing.trace_extraction(
                case_id="child_case",
                model="claude-sonnet-4-5-20250929",
                provider_id="anthropic",
                input_tokens=10,
                output_tokens=5,
                parent_trace_id="PARENT-TRACE-123",
                parent_span_id="PARENT-SPAN-456",
            )
        ctx = mock_client.start_observation.call_args.kwargs["trace_context"]
        assert ctx is not None
        assert ctx["trace_id"] == "PARENT-TRACE-123"
        assert ctx["parent_span_id"] == "PARENT-SPAN-456"

    def test_trace_with_parent_id_but_no_span_id_omits_parent_span(
        self, monkeypatch
    ) -> None:
        """parent_trace_id sin parent_span_id genera trace_context sin parent_span_id."""
        _patch_settings_enabled(monkeypatch, True)
        mock_client = MagicMock()
        mock_client.start_observation.return_value = MagicMock()
        with patch("langfuse.Langfuse", return_value=mock_client):
            tracing.trace_extraction(
                case_id="x",
                model="claude-sonnet-4-5-20250929",
                provider_id="anthropic",
                input_tokens=10,
                output_tokens=5,
                parent_trace_id="PARENT-T",
            )
        ctx = mock_client.start_observation.call_args.kwargs["trace_context"]
        assert ctx == {"trace_id": "PARENT-T"}

    def test_anthropic_provider_propagates_parent_trace_id(self, monkeypatch) -> None:
        """AnthropicProvider.extract debe pasar parent_trace_id desde ExtractionRequest."""
        _patch_settings_enabled(monkeypatch, True)

        from clinical_extractor.providers import AnthropicProvider

        anth_client = MagicMock()
        anth_client.messages.create.return_value = _mock_anthropic_response(_valid_payload())
        provider = AnthropicProvider(client=anth_client)
        request_with_parent = ExtractionRequest(
            document_text="Test.",
            prompt=get_active_prompt(),
            model_id="claude-sonnet-4-5-20250929",
            max_retries=2,
            initial_backoff=0.001,
            max_backoff=0.001,
            case_id="propagation_case",
            parent_trace_id="API-TRACE-XYZ",
            parent_span_id="API-SPAN-789",
        )

        # Espía sobre trace_extraction (el path real del provider).
        with patch("clinical_extractor.tracing.trace_extraction") as mock_trace:
            provider.extract(request_with_parent)

        mock_trace.assert_called_once()
        kwargs = mock_trace.call_args.kwargs
        assert kwargs["parent_trace_id"] == "API-TRACE-XYZ"
        assert kwargs["parent_span_id"] == "API-SPAN-789"

    def test_marks_as_error_when_extraction_failed(self, monkeypatch) -> None:
        _patch_settings_enabled(monkeypatch, True)
        mock_client = MagicMock()
        mock_generation = MagicMock()
        mock_client.start_observation.return_value = mock_generation

        with patch("langfuse.Langfuse", return_value=mock_client):
            tracing.trace_extraction(
                case_id="failing_case",
                model="claude-sonnet-4-5-20250929",
                provider_id="anthropic",
                error="ConnectionError: API down",
            )

        call_kwargs = mock_client.start_observation.call_args.kwargs
        assert call_kwargs["level"] == "ERROR"
        assert "ConnectionError" in call_kwargs["status_message"]

    def test_cost_details_omitted_when_model_unknown(self, monkeypatch) -> None:
        """Modelo no en la tabla de pricing → cost_details = None (no se setea)."""
        _patch_settings_enabled(monkeypatch, True)
        mock_client = MagicMock()
        mock_client.start_observation.return_value = MagicMock()

        with patch("langfuse.Langfuse", return_value=mock_client):
            tracing.trace_extraction(
                case_id="x",
                model="unknown-model-99",
                provider_id="anthropic",
                input_tokens=100,
                output_tokens=50,
            )

        call_kwargs = mock_client.start_observation.call_args.kwargs
        assert call_kwargs["cost_details"] is None


# =========================================================================
# AnthropicProvider.extract — integración con tracing
# =========================================================================


class TestAnthropicProviderTracingIntegration:
    def test_calls_trace_extraction_on_success(self) -> None:
        """En path exitoso debe llamar trace_extraction con los tokens correctos."""
        client = MagicMock()
        client.messages.create.return_value = _mock_anthropic_response(_valid_payload())
        provider = AnthropicProvider(client=client)

        # _safe_trace en el provider importa trace_extraction diferido desde
        # clinical_extractor.tracing, así que patcheamos en ese path.
        with patch("clinical_extractor.tracing.trace_extraction") as mock_trace:
            response = provider.extract(_make_request(case_id="trace_case_01"))

        assert response.parsed_output["confidence_score"] == 0.9
        mock_trace.assert_called_once()
        call_kwargs = mock_trace.call_args.kwargs
        assert call_kwargs["case_id"] == "trace_case_01"
        assert call_kwargs["model"] == "claude-sonnet-4-5-20250929"
        assert call_kwargs["provider_id"] == "anthropic"
        assert call_kwargs["input_tokens"] == 200
        assert call_kwargs["output_tokens"] == 80
        assert call_kwargs["error"] is None
        assert call_kwargs["output_json"] is not None

    def test_calls_trace_extraction_on_error_then_reraises(self) -> None:
        """Si la extracción falla, debe trace con error=... y re-raise la excepción."""
        client = MagicMock()
        client.messages.create.side_effect = _make_connection_error()
        provider = AnthropicProvider(client=client)

        with patch(
            "clinical_extractor.tracing.trace_extraction"
        ) as mock_trace, pytest.raises(AnthropicExtractionError):
            provider.extract(_make_request(case_id="failing_case"))

        # Verificar que el trace se llamó con error antes de re-raise.
        mock_trace.assert_called_once()
        call_kwargs = mock_trace.call_args.kwargs
        assert call_kwargs["case_id"] == "failing_case"
        assert call_kwargs["error"] is not None
        assert "APIConnectionError" in call_kwargs["error"] or "Connection" in call_kwargs["error"]
        assert call_kwargs["output_json"] is None

    def test_uses_unknown_case_when_case_id_is_none(self) -> None:
        """Sin case_id en el request, el trace usa 'unknown_case' como fallback."""
        client = MagicMock()
        client.messages.create.return_value = _mock_anthropic_response(_valid_payload())
        provider = AnthropicProvider(client=client)

        with patch(
            "clinical_extractor.tracing.trace_extraction"
        ) as mock_trace:
            provider.extract(_make_request(case_id=None))

        call_kwargs = mock_trace.call_args.kwargs
        assert call_kwargs["case_id"] == "unknown_case"

    def test_tracing_failure_does_not_break_extraction(self) -> None:
        """Si trace_extraction lanza algo, extract sigue devolviendo el response."""
        client = MagicMock()
        client.messages.create.return_value = _mock_anthropic_response(_valid_payload())
        provider = AnthropicProvider(client=client)

        with patch(
            "clinical_extractor.tracing.trace_extraction",
            side_effect=RuntimeError("tracing dió fault"),
        ):
            # No debe lanzar — _safe_trace envuelve.
            response = provider.extract(_make_request())

        assert response.parsed_output["confidence_score"] == 0.9
        # Sanity: la llamada a Anthropic sí se hizo.
        client.messages.create.assert_called_once()


# Sanity: que las fixtures del mock no oculten errores reales de import
# (paranoia post-refactor).
def test_module_imports_cleanly() -> None:
    from clinical_extractor import pricing, settings  # noqa: F401
    from clinical_extractor import tracing as _tracing

    assert callable(_tracing.trace_extraction)
    assert callable(_tracing.get_langfuse_client)
    assert callable(_tracing.shutdown_tracing)


# Helper sanity check: serialización de output_json no rompe.
def test_output_json_is_json_serializable_after_pydantic_dump() -> None:
    payload = _valid_payload()
    encoded = json.dumps(payload)
    assert "confidence_score" in encoded
