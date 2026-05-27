"""Tests de integración del tracing en el endpoint ``POST /extract``.

Cubren el flujo end-to-end del API (TestClient → handler → tracing):

- El endpoint llama ``start_extract_trace`` en cada request, aún si
  Langfuse está deshabilitado (retorna None, no rompe).
- En path exitoso, llama ``finish_extract_trace(success=True, ...)``.
- En path de error (extractor lanza), llama ``finish_extract_trace(
  success=False, error=..., ...)`` ANTES de devolver 500.
- El response HTTP sigue siendo correcto (200/500) independientemente
  de lo que pase con Langfuse.
- Si Langfuse está deshabilitado, el extractor NO recibe parent_trace_id
  (sigue siendo None).

Mocks: tracing se mockea con ``patch`` para verificar las llamadas.
``fake_extractor`` (conftest) acepta ``**kwargs`` y por ende
``parent_trace_id``/``parent_span_id`` no rompen los tests existentes.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch


def test_extract_endpoint_calls_start_trace(
    make_client, fake_extractor, minimal_pdf_bytes
) -> None:
    """start_extract_trace se llama una vez por request — incluso si tracing
    está deshabilitado (retorna None pero la llamada SI ocurre)."""
    client = make_client(extractor=fake_extractor)
    with patch("sica_api.routes.extract.start_extract_trace") as mock_start:
        mock_start.return_value = None  # tracing deshabilitado
        response = client.post(
            "/extract",
            files={"file": ("case.pdf", minimal_pdf_bytes, "application/pdf")},
        )
    assert response.status_code == 200
    mock_start.assert_called_once()
    call_kwargs = mock_start.call_args.kwargs
    # ``request_id`` UUID generado por middleware.
    assert "request_id" in call_kwargs
    assert call_kwargs["pdf_filename"] == "case.pdf"
    assert call_kwargs["pdf_size_bytes"] == len(minimal_pdf_bytes)


def test_extract_endpoint_calls_finish_trace_on_success(
    make_client, fake_extractor, minimal_pdf_bytes
) -> None:
    """En path exitoso, finish_extract_trace se llama con success=True y
    output_summary sin PHI (solo confidence/counts)."""
    fake_ctx = {"trace_id": "t-1", "span_id": "s-1", "span": object(), "request_id": "r-1"}
    client = make_client(extractor=fake_extractor)
    with (
        patch("sica_api.routes.extract.start_extract_trace", return_value=fake_ctx),
        patch("sica_api.routes.extract.finish_extract_trace") as mock_finish,
    ):
        response = client.post(
            "/extract",
            files={"file": ("c.pdf", minimal_pdf_bytes, "application/pdf")},
        )

    assert response.status_code == 200
    mock_finish.assert_called_once()
    # Primer arg posicional: trace_context.
    args, kwargs = mock_finish.call_args
    assert args[0] is fake_ctx
    assert kwargs["success"] is True
    assert kwargs["latency_ms"] >= 0
    # output_summary contiene metadata segura, NO el payload completo.
    summary = kwargs.get("output_summary") or {}
    assert summary.get("confidence_score") == 0.91  # del fake_extractor
    assert summary.get("num_evidence_spans") == 0
    # Asegurar que NO se está pasando el payload entero.
    assert "patient_age" not in summary
    assert "notes_summary" not in summary


def test_extract_endpoint_calls_finish_trace_on_error(
    make_client, failing_extractor, minimal_pdf_bytes
) -> None:
    """En path de error, finish se llama con success=False y error=..."""
    fake_ctx = {"trace_id": "t-err", "span_id": "s-err", "span": object(), "request_id": "r-err"}
    client = make_client(extractor=failing_extractor)
    with (
        patch("sica_api.routes.extract.start_extract_trace", return_value=fake_ctx),
        patch("sica_api.routes.extract.finish_extract_trace") as mock_finish,
    ):
        response = client.post(
            "/extract",
            files={"file": ("c.pdf", minimal_pdf_bytes, "application/pdf")},
        )

    assert response.status_code == 500
    mock_finish.assert_called_once()
    args, kwargs = mock_finish.call_args
    assert args[0] is fake_ctx
    assert kwargs["success"] is False
    assert kwargs["error"] is not None
    assert "simulated extractor failure" in kwargs["error"]


def test_extract_works_when_langfuse_disabled(
    make_client, fake_extractor, minimal_pdf_bytes
) -> None:
    """Sin LANGFUSE_*, el endpoint debe responder 200 normalmente.

    Sin mocking del módulo de tracing: usamos la implementación real, que
    cae al fallback de "tracing deshabilitado" porque el conftest borra
    las env vars en cada test.
    """
    client = make_client(extractor=fake_extractor)
    response = client.post(
        "/extract",
        files={"file": ("a.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["confidence_score"] == 0.91


def test_extract_propagates_case_id_from_upload_filename(
    make_client, minimal_pdf_bytes
) -> None:
    """case_id pasado al extractor debe ser el stem del filename del upload,
    NO el tempfile name. Ese era el bug pre-fix (ADR 0007 § Limitación conocida)."""
    received_kwargs: dict[str, Any] = {}

    def _spy_extractor(pdf_path, *, api_key: str, **kwargs: Any) -> dict[str, Any]:
        received_kwargs.update(kwargs)
        return {
            "patient_age": 30,
            "gestational_age_weeks": 25.0,
            "fum": "2025-09-15",
            "fpp": "2026-06-22",
            "active_problems": [],
            "risk_factors": [],
            "lab_results": [],
            "notes_summary": "test",
            "confidence_score": 0.9,
            "evidence_spans": [],
        }

    client = make_client(extractor=_spy_extractor)
    response = client.post(
        "/extract",
        files={"file": ("synthetic_case_01.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    # case_id sin extensión: "synthetic_case_01" (no "synthetic_case_01.pdf").
    assert received_kwargs.get("case_id") == "synthetic_case_01"


def test_extract_case_id_strips_pdf_extension(make_client, minimal_pdf_bytes) -> None:
    """Filename con .pdf debe quedar sin la extensión en el case_id."""
    received_kwargs: dict[str, Any] = {}

    def _spy_extractor(pdf_path, *, api_key: str, **kwargs: Any) -> dict[str, Any]:
        received_kwargs.update(kwargs)
        return {
            "patient_age": 30,
            "gestational_age_weeks": 25.0,
            "fum": "2025-09-15",
            "fpp": "2026-06-22",
            "active_problems": [],
            "risk_factors": [],
            "lab_results": [],
            "notes_summary": "t",
            "confidence_score": 0.9,
            "evidence_spans": [],
        }

    client = make_client(extractor=_spy_extractor)
    client.post(
        "/extract",
        files={
            "file": ("paciente_xyz.pdf", minimal_pdf_bytes, "application/pdf"),
        },
    )
    assert received_kwargs.get("case_id") == "paciente_xyz"


def test_extract_case_id_in_trace_metadata(
    make_client, fake_extractor, minimal_pdf_bytes
) -> None:
    """start_extract_trace debe recibir pdf_filename con el nombre original."""
    client = make_client(extractor=fake_extractor)
    with patch("sica_api.routes.extract.start_extract_trace") as mock_start:
        mock_start.return_value = None
        client.post(
            "/extract",
            files={"file": ("synthetic_case_05_dm.pdf", minimal_pdf_bytes, "application/pdf")},
        )
    mock_start.assert_called_once()
    # El span padre lleva el filename original (sin stripear) para auditoría.
    assert mock_start.call_args.kwargs["pdf_filename"] == "synthetic_case_05_dm.pdf"


def test_extract_propagates_trace_ids_to_extractor(
    make_client, minimal_pdf_bytes
) -> None:
    """Cuando trace_context tiene IDs, el extractor los recibe en kwargs."""
    received_kwargs: dict[str, Any] = {}

    def _spy_extractor(pdf_path, *, api_key: str, **kwargs: Any) -> dict[str, Any]:
        received_kwargs.update(kwargs)
        return {
            "patient_age": 30,
            "gestational_age_weeks": 25.0,
            "fum": "2025-09-15",
            "fpp": "2026-06-22",
            "active_problems": [],
            "risk_factors": [],
            "lab_results": [],
            "notes_summary": "test",
            "confidence_score": 0.9,
            "evidence_spans": [],
        }

    fake_ctx = {
        "trace_id": "TRACE-PROPAGATED",
        "span_id": "SPAN-PROPAGATED",
        "span": object(),
        "request_id": "r-x",
    }
    client = make_client(extractor=_spy_extractor)
    with (
        patch("sica_api.routes.extract.start_extract_trace", return_value=fake_ctx),
        patch("sica_api.routes.extract.finish_extract_trace"),
    ):
        response = client.post(
            "/extract",
            files={"file": ("x.pdf", minimal_pdf_bytes, "application/pdf")},
        )
    assert response.status_code == 200
    # Verificar que los IDs llegaron al extractor.
    assert received_kwargs.get("parent_trace_id") == "TRACE-PROPAGATED"
    assert received_kwargs.get("parent_span_id") == "SPAN-PROPAGATED"


def test_extract_passes_none_to_extractor_when_tracing_disabled(
    make_client, minimal_pdf_bytes
) -> None:
    """Sin trace_context, parent_trace_id/parent_span_id llegan como None."""
    received_kwargs: dict[str, Any] = {}

    def _spy_extractor(pdf_path, *, api_key: str, **kwargs: Any) -> dict[str, Any]:
        received_kwargs.update(kwargs)
        return {
            "patient_age": 30,
            "gestational_age_weeks": 25.0,
            "fum": "2025-09-15",
            "fpp": "2026-06-22",
            "active_problems": [],
            "risk_factors": [],
            "lab_results": [],
            "notes_summary": "test",
            "confidence_score": 0.9,
            "evidence_spans": [],
        }

    client = make_client(extractor=_spy_extractor)
    # No mockeamos tracing — el conftest deshabilita Langfuse y
    # start_extract_trace retorna None → kwargs van None al extractor.
    response = client.post(
        "/extract",
        files={"file": ("x.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    assert received_kwargs.get("parent_trace_id") is None
    assert received_kwargs.get("parent_span_id") is None


def test_extract_response_to_client_is_not_redacted(
    make_client, minimal_pdf_bytes
) -> None:
    """ADR-0009: la redaction sólo aplica al payload de Langfuse.

    El response HTTP que el cliente recibe debe llevar los datos completos.
    Verifica que un fake_extractor que devuelve un payload "como si" tuviera
    PHI (campos clínicos normales — el extractor real NO produce dichos
    campos PHI, pero defensivamente verificamos que el flujo no redacta el
    response del API).
    """
    def _extractor_with_clinical_data(pdf_path, *, api_key: str, **kwargs: Any) -> dict[str, Any]:
        return {
            "patient_age": 30,
            "gestational_age_weeks": 24.5,
            "fum": "2025-12-01",
            "fpp": "2026-09-07",
            "active_problems": ["Diabetes gestacional"],
            "risk_factors": ["Edad materna avanzada"],
            "lab_results": [],
            "notes_summary": "Paciente con control adecuado, factores de riesgo controlados.",
            "confidence_score": 0.92,
            "evidence_spans": [],
        }

    client = make_client(extractor=_extractor_with_clinical_data)
    response = client.post(
        "/extract",
        files={"file": ("synthetic_demo.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    # Datos clínicos del response NO están redactados — el cliente HTTP
    # recibe el JSON completo (la redacción aplica solo al SDK Langfuse).
    assert body["patient_age"] == 30
    assert body["active_problems"] == ["Diabetes gestacional"]
    assert "Paciente con control" in body["notes_summary"]
    assert "[REDACTED]" not in body["notes_summary"]


def test_extract_start_trace_sanitizes_phi_filename(
    make_client, fake_extractor, minimal_pdf_bytes, monkeypatch
) -> None:
    """ADR-0009: pdf_filename con potencial PHI llega redactado al SDK.

    Cuando el upload trae un filename sin prefijo seguro (e.g.
    ``maria_lopez_hc.pdf``), el span padre en Langfuse debe llevar
    ``[REDACTED].pdf`` en metadata.pdf_filename — no el filename original.
    Verifica el contrato extremo a extremo a través del endpoint.
    """
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-x")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-x")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://test.local")
    from sica_api import tracing as _tracing
    from sica_api.settings import get_settings

    get_settings.cache_clear()
    _tracing.get_langfuse_client.cache_clear()

    from unittest.mock import MagicMock as _Mock

    mock_span = _Mock(trace_id="t-1", id="s-1")
    mock_client = _Mock()
    mock_client.start_observation.return_value = mock_span

    with patch("langfuse.Langfuse", return_value=mock_client):
        client = make_client(extractor=fake_extractor)
        response = client.post(
            "/extract",
            files={
                "file": ("maria_lopez_hc.pdf", minimal_pdf_bytes, "application/pdf"),
            },
        )

    assert response.status_code == 200
    # El span se creó con filename redactado en metadata.
    call_kwargs = mock_client.start_observation.call_args.kwargs
    assert call_kwargs["metadata"]["pdf_filename"] == "[REDACTED].pdf"


def test_extract_finish_trace_sdk_failure_does_not_break_response(
    make_client, fake_extractor, minimal_pdf_bytes, monkeypatch
) -> None:
    """Si el SDK de Langfuse lanza dentro de finish_extract_trace, el
    response sigue siendo 200. Patcheamos el SDK adentro del try/except
    interno (no el wrapper), que es lo que realmente cubre el contrato
    "tracing nunca rompe el response".
    """
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-x")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-x")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://test.local")
    from sica_api import tracing as _tracing
    from sica_api.settings import get_settings

    get_settings.cache_clear()
    _tracing.get_langfuse_client.cache_clear()

    from unittest.mock import MagicMock as _Mock

    mock_span = _Mock(trace_id="t", id="s")
    mock_span.update.side_effect = RuntimeError("update boom")  # falla en finish
    mock_client = _Mock()
    mock_client.start_observation.return_value = mock_span

    with patch("langfuse.Langfuse", return_value=mock_client):
        client = make_client(extractor=fake_extractor)
        response = client.post(
            "/extract",
            files={"file": ("x.pdf", minimal_pdf_bytes, "application/pdf")},
        )

    assert response.status_code == 200  # tracing falla, response intacto
