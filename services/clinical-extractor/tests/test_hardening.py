"""Tests del production hardening (Bloque 3): retry, telemetry, batch.

Estos tests NO consumen la API de Anthropic. Toda interacción con el
cliente está mockeada. El propósito es validar la mecánica de retry,
backoff, abstención frente a errores no-retriables, emisión de telemetría
y procesamiento batch.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import anthropic
import httpx
import pytest

from clinical_extractor import telemetry
from clinical_extractor.cli import _run_batch
from clinical_extractor.extractor import (
    ExtractionError,
    _backoff_delay,
    _call_model_with_retry,
    extract_from_pdf,
)
from clinical_extractor.prompts import get_active_prompt
from clinical_extractor.schemas import ObstetricSummary

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_valid_pdf_bytes() -> bytes:
    """PDF mínimo válido con una línea de texto extraíble."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length 44>>stream\n"
        b"BT /F1 12 Tf 50 750 Td (HISTORIA CLINICA TEST) Tj ET\n"
        b"endstream endobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000052 00000 n \n"
        b"0000000095 00000 n \n"
        b"0000000182 00000 n \n"
        b"0000000270 00000 n \n"
        b"trailer<</Size 6/Root 1 0 R>>\n"
        b"startxref\n328\n%%EOF\n"
    )


def _make_minimal_pdf(tmp_path: Path, name: str = "case.pdf") -> Path:
    p = tmp_path / name
    p.write_bytes(_minimal_valid_pdf_bytes())
    return p


def _mock_anthropic_response(payload: dict) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = "record_obstetric_summary"
    block.input = payload
    response = MagicMock()
    response.content = [block]
    response.stop_reason = "tool_use"
    response.usage = MagicMock(input_tokens=123, output_tokens=45)
    return response


def _valid_summary_payload() -> dict:
    return {
        "confidence_score": 0.9,
        "active_problems": ["Anemia leve gestacional"],
        "risk_factors": ["Cesárea previa"],
        "lab_results": [],
        "evidence_spans": [],
        "notes_summary": "Test case.",
        "patient_age": 32,
        "gestational_age_weeks": 28.0,
    }


def _make_connection_error() -> anthropic.APIConnectionError:
    # APIConnectionError requires a `request` kwarg in this SDK version.
    return anthropic.APIConnectionError(
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    )


def _make_auth_error() -> anthropic.AuthenticationError:
    # Build a real httpx.Response so the SDK can populate status_code.
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


# ---------------------------------------------------------------------------
# Backoff
# ---------------------------------------------------------------------------


class TestBackoff:
    def test_grows_exponentially(self) -> None:
        # Use enough samples so jitter doesn't dominate the assertion.
        d0 = sum(_backoff_delay(0, 1.0, 16.0) for _ in range(200)) / 200
        d2 = sum(_backoff_delay(2, 1.0, 16.0) for _ in range(200)) / 200
        assert d0 < d2

    def test_caps_at_maximum(self) -> None:
        d = _backoff_delay(20, 1.0, 16.0)
        # Max is 16 ± 20% jitter, so ≤ 19.2
        assert d <= 19.3


# ---------------------------------------------------------------------------
# Retry semantics on the inner call_model
# ---------------------------------------------------------------------------


class TestCallModelRetry:
    def test_retries_on_connection_error_then_succeeds(self) -> None:
        client = MagicMock()
        client.messages.create.side_effect = [
            _make_connection_error(),
            _make_connection_error(),
            _mock_anthropic_response(_valid_summary_payload()),
        ]
        sleeps: list[float] = []
        payload, usage, retries = _call_model_with_retry(
            client=client,
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            prompt=get_active_prompt(),
            document_text="dummy text",
            max_retries=3,
            initial_backoff=0.001,
            max_backoff=0.001,
            sleep_fn=sleeps.append,
        )
        assert retries == 2
        assert payload["confidence_score"] == 0.9
        assert usage == {"input_tokens": 123, "output_tokens": 45}
        assert len(sleeps) == 2  # two retries → two sleeps

    def test_does_not_retry_on_authentication_error(self) -> None:
        client = MagicMock()
        client.messages.create.side_effect = _make_auth_error()
        sleeps: list[float] = []
        with pytest.raises(anthropic.AuthenticationError):
            _call_model_with_retry(
                client=client,
                model="claude-sonnet-4-5-20250929",
                max_tokens=1024,
                prompt=get_active_prompt(),
                document_text="dummy text",
                max_retries=3,
                initial_backoff=0.001,
                max_backoff=0.001,
                sleep_fn=sleeps.append,
            )
        assert client.messages.create.call_count == 1
        assert sleeps == []

    def test_exhausts_retries_and_raises_extraction_error(self) -> None:
        client = MagicMock()
        client.messages.create.side_effect = _make_connection_error()
        sleeps: list[float] = []
        with pytest.raises(ExtractionError, match="Reintentos agotados"):
            _call_model_with_retry(
                client=client,
                model="claude-sonnet-4-5-20250929",
                max_tokens=1024,
                prompt=get_active_prompt(),
                document_text="dummy text",
                max_retries=2,
                initial_backoff=0.001,
                max_backoff=0.001,
                sleep_fn=sleeps.append,
            )
        assert client.messages.create.call_count == 3  # original + 2 retries
        assert len(sleeps) == 2

    def test_retries_on_rate_limit_error(self) -> None:
        body = b'{"error":{"type":"rate_limit_error","message":"slow down"}}'
        rate_limit = anthropic.RateLimitError(
            message="slow down",
            response=httpx.Response(
                status_code=429,
                request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
                content=body,
                headers={"content-type": "application/json"},
            ),
            body=json.loads(body),
        )
        client = MagicMock()
        client.messages.create.side_effect = [
            rate_limit,
            _mock_anthropic_response(_valid_summary_payload()),
        ]
        payload, _, retries = _call_model_with_retry(
            client=client,
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            prompt=get_active_prompt(),
            document_text="dummy text",
            max_retries=2,
            initial_backoff=0.001,
            max_backoff=0.001,
            sleep_fn=lambda _s: None,
        )
        assert retries == 1
        assert payload["confidence_score"] == 0.9


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------


class _CapturingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[dict] = []

    def emit(self, record: logging.LogRecord) -> None:
        payload = getattr(record, "payload", None)
        if isinstance(payload, dict):
            self.records.append(payload)


@pytest.fixture
def capture_telemetry():
    logger = logging.getLogger(telemetry.TELEMETRY_LOGGER_NAME)
    handler = _CapturingHandler()
    original_level = logger.level
    original_propagate = logger.propagate
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(original_level)
        logger.propagate = original_propagate


class TestTelemetry:
    def test_emit_on_success(self, capture_telemetry, tmp_path: Path) -> None:
        pdf = _make_minimal_pdf(tmp_path)
        client = MagicMock()
        client.messages.create.return_value = _mock_anthropic_response(
            _valid_summary_payload()
        )

        summary = extract_from_pdf(pdf, client=client)
        assert isinstance(summary, ObstetricSummary)
        assert len(capture_telemetry.records) == 1
        rec = capture_telemetry.records[0]
        expected_keys = {
            "timestamp",
            "operation_id",
            "pdf_path",
            "pdf_size_bytes",
            "pages_extracted",
            "model_used",
            "prompt_version",
            "latency_ms",
            "retry_count",
            "success",
            "error_type",
            "token_usage",
        }
        assert expected_keys.issubset(rec.keys())
        assert rec["success"] is True
        assert rec["error_type"] is None
        assert rec["retry_count"] == 0
        assert rec["pages_extracted"] == 1
        assert rec["pdf_size_bytes"] == pdf.stat().st_size
        assert rec["token_usage"] == {"input_tokens": 123, "output_tokens": 45}
        assert rec["model_used"]
        assert rec["prompt_version"]

    def test_emit_on_failure_with_error_type(
        self, capture_telemetry, tmp_path: Path
    ) -> None:
        pdf = _make_minimal_pdf(tmp_path)
        client = MagicMock()
        client.messages.create.side_effect = _make_auth_error()

        with pytest.raises(anthropic.AuthenticationError):
            extract_from_pdf(pdf, client=client)

        assert len(capture_telemetry.records) == 1
        rec = capture_telemetry.records[0]
        assert rec["success"] is False
        assert rec["error_type"] == "AuthenticationError"

    def test_no_phi_in_record(self, capture_telemetry, tmp_path: Path) -> None:
        """El record no debe llevar contenido del PDF ni del output."""
        pdf = _make_minimal_pdf(tmp_path)
        client = MagicMock()
        client.messages.create.return_value = _mock_anthropic_response(
            _valid_summary_payload()
        )
        extract_from_pdf(pdf, client=client)
        rec = capture_telemetry.records[0]
        # Whitelist de keys permitidos — si alguien agrega un campo nuevo
        # debe pasar por revisión explícita.
        allowed = {
            "timestamp",
            "operation_id",
            "pdf_path",
            "pdf_size_bytes",
            "pages_extracted",
            "model_used",
            "prompt_version",
            "latency_ms",
            "retry_count",
            "success",
            "error_type",
            "token_usage",
        }
        unexpected = set(rec.keys()) - allowed
        assert not unexpected, f"telemetría tiene keys no permitidas: {unexpected}"

    def test_json_line_formatter_serializes_payload(self) -> None:
        record = logging.LogRecord(
            name=telemetry.TELEMETRY_LOGGER_NAME,
            level=logging.INFO,
            pathname=__file__,
            lineno=0,
            msg="telemetry",
            args=(),
            exc_info=None,
        )
        record.payload = {"a": 1, "b": "x"}  # type: ignore[attr-defined]
        formatter = telemetry._JsonLineFormatter()
        line = formatter.format(record)
        parsed = json.loads(line)
        assert parsed == {"a": 1, "b": "x"}

    def test_configure_stream_handler_is_idempotent(self) -> None:
        telemetry.configure_stream_handler()
        telemetry.configure_stream_handler()
        logger = logging.getLogger(telemetry.TELEMETRY_LOGGER_NAME)
        sica_handlers = [
            h for h in logger.handlers if getattr(h, "_sica_telemetry", False)
        ]
        assert len(sica_handlers) == 1


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


class TestExtractBatch:
    def test_processes_multiple_pdfs(self, tmp_path: Path, monkeypatch) -> None:
        # Create 3 minimal PDFs
        pdfs = [_make_minimal_pdf(tmp_path, f"case_{i:02d}.pdf") for i in range(3)]

        def fake_extract(path, **kwargs):
            return ObstetricSummary(confidence_score=0.88)

        monkeypatch.setattr("clinical_extractor.cli.extract_from_pdf", fake_extract)

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        results = asyncio.run(_run_batch(pdfs, out_dir, concurrency=2, model=None, max_tokens=None))

        assert len(results) == 3
        for pdf, out_json, error, _elapsed in results:
            assert error is None
            assert out_json is not None
            assert out_json.exists()
            data = json.loads(out_json.read_text(encoding="utf-8"))
            assert data["confidence_score"] == 0.88
            assert out_json.name == f"{pdf.stem}.json"

    def test_isolates_failures(self, tmp_path: Path, monkeypatch) -> None:
        """Un PDF que falla NO debe abortar la corrida completa."""
        pdfs = [_make_minimal_pdf(tmp_path, f"case_{i:02d}.pdf") for i in range(3)]

        call_count = {"n": 0}

        def fake_extract(path, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise ExtractionError("simulated mid-batch failure")
            return ObstetricSummary(confidence_score=0.5)

        monkeypatch.setattr("clinical_extractor.cli.extract_from_pdf", fake_extract)

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        results = asyncio.run(_run_batch(pdfs, out_dir, concurrency=1, model=None, max_tokens=None))
        errors = [r for r in results if r[2] is not None]
        successes = [r for r in results if r[2] is None]
        assert len(errors) == 1
        assert len(successes) == 2
        assert "simulated mid-batch failure" in errors[0][2]

    def test_respects_concurrency_semaphore(self, tmp_path: Path, monkeypatch) -> None:
        """Concurrency=2 limita a 2 PDFs in-flight simultáneos."""
        pdfs = [_make_minimal_pdf(tmp_path, f"case_{i:02d}.pdf") for i in range(6)]
        in_flight = {"current": 0, "peak": 0}
        lock = asyncio.Lock()

        async def fake_extract_one(pdf, out_dir, sem, model, max_tokens):
            async with sem:
                async with lock:
                    in_flight["current"] += 1
                    in_flight["peak"] = max(in_flight["peak"], in_flight["current"])
                await asyncio.sleep(0.05)
                async with lock:
                    in_flight["current"] -= 1
                return pdf, out_dir / f"{pdf.stem}.json", None, 0.05

        monkeypatch.setattr("clinical_extractor.cli._extract_one", fake_extract_one)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        asyncio.run(_run_batch(pdfs, out_dir, concurrency=2, model=None, max_tokens=None))
        assert in_flight["peak"] <= 2
