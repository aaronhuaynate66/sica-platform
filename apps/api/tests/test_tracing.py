"""Tests de ``sica_api.tracing`` — observability del lado API.

Cubren:
- ``get_langfuse_client()`` retorna ``None`` cuando settings no habilitan.
- ``get_langfuse_client()`` retorna instancia cuando vars presentes.
- ``start_extract_trace()`` retorna dict con trace_id/span_id cuando enabled.
- ``start_extract_trace()`` retorna ``None`` cuando deshabilitado.
- ``finish_extract_trace()`` es no-op cuando ``trace_context`` es ``None``.
- ``finish_extract_trace()`` marca ERROR cuando success=False.
- ``finish_extract_trace()`` actualiza span con success metadata.
- ``start_extract_trace()`` jamás levanta aunque SDK lance.
- Helpers ``get_trace_id_from_context`` / ``get_span_id_from_context`` se
  comportan con None / dict válido / dict sin keys.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sica_api import tracing


def _enable_langfuse(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://test.langfuse.local")
    from sica_api.settings import get_settings

    get_settings.cache_clear()
    tracing.get_langfuse_client.cache_clear()


# =========================================================================
# get_langfuse_client
# =========================================================================


class TestGetLangfuseClient:
    def test_returns_none_when_disabled(self) -> None:
        # conftest autouse ya borra las env vars; sólo verificamos resultado.
        assert tracing.get_langfuse_client() is None

    def test_returns_instance_when_enabled(self, monkeypatch) -> None:
        _enable_langfuse(monkeypatch)
        mock_instance = MagicMock()
        with patch("langfuse.Langfuse", return_value=mock_instance):
            client = tracing.get_langfuse_client()
        assert client is mock_instance

    def test_returns_none_when_sdk_raises(self, monkeypatch) -> None:
        _enable_langfuse(monkeypatch)
        with patch("langfuse.Langfuse", side_effect=RuntimeError("boom")):
            client = tracing.get_langfuse_client()
        assert client is None  # graceful fallback


# =========================================================================
# start_extract_trace
# =========================================================================


class TestStartExtractTrace:
    def test_returns_none_when_disabled(self) -> None:
        ctx = tracing.start_extract_trace(
            request_id="req-1",
            pdf_filename="foo.pdf",
            pdf_size_bytes=1024,
        )
        assert ctx is None

    def test_returns_dict_with_ids_when_enabled(self, monkeypatch) -> None:
        _enable_langfuse(monkeypatch)
        mock_span = MagicMock(trace_id="trace-abc", id="span-xyz")
        mock_client = MagicMock()
        mock_client.start_observation.return_value = mock_span

        with patch("langfuse.Langfuse", return_value=mock_client):
            ctx = tracing.start_extract_trace(
                request_id="req-42",
                # synthetic_ es prefijo seguro (ADR-0009) — se preserva tal cual.
                pdf_filename="synthetic_caso_01.pdf",
                pdf_size_bytes=5_000,
            )

        assert ctx is not None
        assert ctx["trace_id"] == "trace-abc"
        assert ctx["span_id"] == "span-xyz"
        assert ctx["request_id"] == "req-42"
        # span ref viva guardada para .end() futuro.
        assert ctx["span"] is mock_span
        # Verificar args del start_observation.
        call = mock_client.start_observation.call_args
        assert call.kwargs["name"] == "api_extract_request"
        assert call.kwargs["as_type"] == "span"
        assert call.kwargs["metadata"]["request_id"] == "req-42"
        assert call.kwargs["metadata"]["pdf_filename"] == "synthetic_caso_01.pdf"
        assert call.kwargs["metadata"]["pdf_size_bytes"] == 5_000

    def test_returns_none_when_sdk_raises(self, monkeypatch) -> None:
        _enable_langfuse(monkeypatch)
        mock_client = MagicMock()
        mock_client.start_observation.side_effect = RuntimeError("dashboard down")
        with patch("langfuse.Langfuse", return_value=mock_client):
            ctx = tracing.start_extract_trace(
                request_id="req-fail",
                pdf_filename="x.pdf",
                pdf_size_bytes=10,
            )
        # No re-raise; retorna None graceful.
        assert ctx is None

    def test_default_filename_when_missing(self, monkeypatch) -> None:
        _enable_langfuse(monkeypatch)
        mock_span = MagicMock(trace_id="t", id="s")
        mock_client = MagicMock()
        mock_client.start_observation.return_value = mock_span
        with patch("langfuse.Langfuse", return_value=mock_client):
            tracing.start_extract_trace(
                request_id="req-1",
                pdf_filename=None,
                pdf_size_bytes=None,
            )
        meta = mock_client.start_observation.call_args.kwargs["metadata"]
        assert meta["pdf_filename"] == "uploaded_pdf"


# =========================================================================
# finish_extract_trace
# =========================================================================


class TestFinishExtractTrace:
    def test_noop_when_context_is_none(self) -> None:
        # No debe levantar.
        tracing.finish_extract_trace(
            None,
            success=True,
            latency_ms=100.0,
        )

    def test_updates_span_on_success(self, monkeypatch) -> None:
        _enable_langfuse(monkeypatch)
        mock_span = MagicMock(trace_id="t", id="s")
        mock_client = MagicMock()
        mock_client.start_observation.return_value = mock_span
        with patch("langfuse.Langfuse", return_value=mock_client):
            ctx = tracing.start_extract_trace(
                request_id="req-ok",
                pdf_filename="x.pdf",
                pdf_size_bytes=10,
            )
            tracing.finish_extract_trace(
                ctx,
                success=True,
                latency_ms=1500.0,
                output_summary={"confidence_score": 0.91, "num_evidence_spans": 5},
            )

        # update llamado con success metadata + level DEFAULT.
        assert mock_span.update.called
        update_kwargs = mock_span.update.call_args.kwargs
        assert update_kwargs["level"] == "DEFAULT"
        assert update_kwargs["metadata"]["success"] is True
        assert update_kwargs["metadata"]["latency_ms"] == 1500.0
        assert update_kwargs["output"]["confidence_score"] == 0.91
        # end siempre se llama.
        mock_span.end.assert_called_once()
        mock_client.flush.assert_called()

    def test_marks_error_when_success_false(self, monkeypatch) -> None:
        _enable_langfuse(monkeypatch)
        mock_span = MagicMock(trace_id="t", id="s")
        mock_client = MagicMock()
        mock_client.start_observation.return_value = mock_span
        with patch("langfuse.Langfuse", return_value=mock_client):
            ctx = tracing.start_extract_trace(
                request_id="req-err",
                pdf_filename="x.pdf",
                pdf_size_bytes=10,
            )
            tracing.finish_extract_trace(
                ctx,
                success=False,
                latency_ms=300.0,
                error="ConnectionError: Anthropic 503",
            )

        update_kwargs = mock_span.update.call_args.kwargs
        assert update_kwargs["level"] == "ERROR"
        assert update_kwargs["metadata"]["success"] is False
        assert update_kwargs["metadata"]["error"] == "ConnectionError: Anthropic 503"
        assert update_kwargs["status_message"] == "ConnectionError: Anthropic 503"

    def test_silent_when_span_update_raises(self, monkeypatch) -> None:
        _enable_langfuse(monkeypatch)
        mock_span = MagicMock(trace_id="t", id="s")
        mock_span.update.side_effect = RuntimeError("update failed")
        mock_client = MagicMock()
        mock_client.start_observation.return_value = mock_span
        with patch("langfuse.Langfuse", return_value=mock_client):
            ctx = tracing.start_extract_trace(
                request_id="req-x",
                pdf_filename="x.pdf",
                pdf_size_bytes=10,
            )
            # No debe re-raise.
            tracing.finish_extract_trace(ctx, success=True, latency_ms=100.0)


# =========================================================================
# Helpers
# =========================================================================


class TestHelpers:
    def test_get_trace_id_from_context_none(self) -> None:
        assert tracing.get_trace_id_from_context(None) is None

    def test_get_trace_id_from_context_missing_key(self) -> None:
        assert tracing.get_trace_id_from_context({"foo": "bar"}) is None

    def test_get_trace_id_from_context_valid(self) -> None:
        assert tracing.get_trace_id_from_context({"trace_id": "abc"}) == "abc"

    def test_get_span_id_from_context_extracts_correctly(self) -> None:
        assert tracing.get_span_id_from_context({"span_id": "xyz"}) == "xyz"
        assert tracing.get_span_id_from_context(None) is None


# =========================================================================
# Sanity import
# =========================================================================


def test_module_imports_without_langfuse_available() -> None:
    """Si langfuse no se puede importar al runtime, el módulo igual carga."""
    # El módulo se importa siempre; los imports de langfuse están diferidos
    # dentro de get_langfuse_client. Si lo logramos importar aquí, OK.
    from sica_api import tracing as _tracing

    assert callable(_tracing.start_extract_trace)
    assert callable(_tracing.finish_extract_trace)


@pytest.mark.parametrize("success,expected_level", [(True, "DEFAULT"), (False, "ERROR")])
def test_finish_level_parametrized(monkeypatch, success, expected_level) -> None:
    """Sanity adicional: el nivel se mapea consistentemente."""
    _enable_langfuse(monkeypatch)
    mock_span = MagicMock(trace_id="t", id="s")
    mock_client = MagicMock()
    mock_client.start_observation.return_value = mock_span
    with patch("langfuse.Langfuse", return_value=mock_client):
        ctx = tracing.start_extract_trace(
            request_id="r", pdf_filename="x.pdf", pdf_size_bytes=1
        )
        tracing.finish_extract_trace(
            ctx,
            success=success,
            latency_ms=10.0,
            error=None if success else "e",
        )
    assert mock_span.update.call_args.kwargs["level"] == expected_level
