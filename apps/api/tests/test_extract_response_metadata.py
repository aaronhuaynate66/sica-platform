"""Tests para el bloque ``metadata`` del response 200 de POST /extract.

Estos tests cubren el contrato aditivo introducido en commit pendiente:
los campos del ``ObstetricSummary`` permanecen en el top-level del JSON
y se suma un campo ``metadata`` con la trazabilidad operacional.

Cada test usa un ``fake_extractor_with_metadata`` que **llena**
``metadata_out`` (igual que el ``_default_extractor`` real). El fixture
``fake_extractor`` original (que NO llena metadata_out) se mantiene
para validar el path de fallback en ``test_metadata_falls_back_when_extractor_skips``.
"""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def fake_extractor_with_metadata():
    """Fake que retorna summary + llena metadata_out con campos realistas."""

    def _fake(
        pdf_path,
        *,
        api_key: str,
        metadata_out: dict[str, Any] | None = None,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        if metadata_out is not None:
            metadata_out.update(
                {
                    "operation_id": "op-uuid-1234",
                    "provider_id": "anthropic",
                    "model_used": "claude-sonnet-4-5-20250929",
                    "prompt_version": "0.1.0",
                    "prompt_hash": "9241ec0d2de94600c1d2",
                    "input_tokens": 4261,
                    "output_tokens": 1251,
                    "cost_usd": 0.031548,
                    "latency_ms": 22500,
                    "retry_count": 0,
                    "success": True,
                    "error_type": None,
                }
            )
        return {
            "patient_age": 28,
            "gestational_age_weeks": 16.3,
            "fum": "2023-12-27",
            "fpp": "2024-10-03",
            "active_problems": ["Sobrepeso pre-gestacional"],
            "risk_factors": ["Antecedente familiar DM2"],
            "lab_results": [],
            "notes_summary": "Test summary",
            "confidence_score": 0.95,
            "evidence_spans": [],
        }

    return _fake


# ---------------------------------------------------------------------------
# 1. Contrato existente NO se rompe
# ---------------------------------------------------------------------------


def test_existing_response_fields_unchanged(
    make_client, fake_extractor_with_metadata, minimal_pdf_bytes
):
    """El frontend antiguo lee campos del summary al top-level y sigue funcionando."""
    client = make_client(extractor=fake_extractor_with_metadata)
    response = client.post(
        "/extract",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["patient_age"] == 28
    assert body["gestational_age_weeks"] == 16.3
    assert body["confidence_score"] == 0.95
    assert body["active_problems"] == ["Sobrepeso pre-gestacional"]
    # X-Request-ID sigue en headers
    assert "X-Request-ID" in response.headers


def test_extract_response_includes_metadata_field(
    make_client, fake_extractor_with_metadata, minimal_pdf_bytes
):
    """El campo nuevo ``metadata`` aparece al mismo nivel que los campos del summary."""
    client = make_client(extractor=fake_extractor_with_metadata)
    response = client.post(
        "/extract",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert "metadata" in body
    assert isinstance(body["metadata"], dict)


# ---------------------------------------------------------------------------
# 2. Sub-campos de metadata
# ---------------------------------------------------------------------------


def test_metadata_includes_provider_id(
    make_client, fake_extractor_with_metadata, minimal_pdf_bytes
):
    client = make_client(extractor=fake_extractor_with_metadata)
    response = client.post(
        "/extract",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.json()["metadata"]["provider_id"] == "anthropic"


def test_metadata_includes_model_used(
    make_client, fake_extractor_with_metadata, minimal_pdf_bytes
):
    client = make_client(extractor=fake_extractor_with_metadata)
    response = client.post(
        "/extract",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.json()["metadata"]["model_used"] == "claude-sonnet-4-5-20250929"


def test_metadata_includes_prompt_version(
    make_client, fake_extractor_with_metadata, minimal_pdf_bytes
):
    client = make_client(extractor=fake_extractor_with_metadata)
    response = client.post(
        "/extract",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.json()["metadata"]["prompt_version"] == "0.1.0"


def test_metadata_includes_prompt_hash(
    make_client, fake_extractor_with_metadata, minimal_pdf_bytes
):
    """El hash se eco-ea tal como vino del registry (no se trunca en el handler)."""
    client = make_client(extractor=fake_extractor_with_metadata)
    response = client.post(
        "/extract",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    # registry.short_hash ya son 8 chars; el fake retorna 20 para verificar
    # que NO se trunca dentro del handler — la responsabilidad del corto
    # está en el registry.
    assert response.json()["metadata"]["prompt_hash"] == "9241ec0d2de94600c1d2"


def test_metadata_includes_cost_usd(
    make_client, fake_extractor_with_metadata, minimal_pdf_bytes
):
    client = make_client(extractor=fake_extractor_with_metadata)
    response = client.post(
        "/extract",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.json()["metadata"]["cost_usd"] == 0.031548


def test_metadata_includes_token_counts(
    make_client, fake_extractor_with_metadata, minimal_pdf_bytes
):
    client = make_client(extractor=fake_extractor_with_metadata)
    response = client.post(
        "/extract",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    metadata = response.json()["metadata"]
    assert metadata["input_tokens"] == 4261
    assert metadata["output_tokens"] == 1251


def test_metadata_includes_latency_and_operation_id(
    make_client, fake_extractor_with_metadata, minimal_pdf_bytes
):
    client = make_client(extractor=fake_extractor_with_metadata)
    response = client.post(
        "/extract",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    metadata = response.json()["metadata"]
    assert metadata["latency_ms"] == 22500
    assert metadata["operation_id"] == "op-uuid-1234"


def test_metadata_includes_request_id_echoed_in_body(
    make_client, fake_extractor_with_metadata, minimal_pdf_bytes
):
    """request_id se eco-ea en body.metadata para clientes que solo persisten body."""
    client = make_client(extractor=fake_extractor_with_metadata)
    response = client.post(
        "/extract",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    body = response.json()
    header_request_id = response.headers["X-Request-ID"]
    assert body["metadata"]["request_id"] == header_request_id


def test_metadata_trace_id_is_null_when_langfuse_disabled(
    make_client, fake_extractor_with_metadata, minimal_pdf_bytes
):
    """Sin LANGFUSE_* vars, trace_id queda None (no crash)."""
    client = make_client(extractor=fake_extractor_with_metadata)
    response = client.post(
        "/extract",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.json()["metadata"]["trace_id"] is None


def test_metadata_success_true_on_happy_path(
    make_client, fake_extractor_with_metadata, minimal_pdf_bytes
):
    client = make_client(extractor=fake_extractor_with_metadata)
    response = client.post(
        "/extract",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    metadata = response.json()["metadata"]
    assert metadata["success"] is True
    assert metadata["error_type"] is None


def test_metadata_falls_back_when_extractor_skips(
    make_client, fake_extractor, minimal_pdf_bytes
):
    """Si el extractor inyectado no llena metadata_out, el handler emite
    defaults razonables — ``unknown`` para model/prompt, ``None`` para tokens,
    ``provider_id`` resuelto del registry, ``latency_ms`` medido por el handler.

    Esto preserva la retrocompatibilidad de tests existentes que usan el
    ``fake_extractor`` legacy.
    """
    client = make_client(extractor=fake_extractor)
    response = client.post(
        "/extract",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    metadata = response.json()["metadata"]
    # Defaults conservadores cuando el extractor no llenó nada
    assert metadata["model_used"] == "unknown"
    assert metadata["prompt_version"] == "unknown"
    assert metadata["input_tokens"] is None
    assert metadata["output_tokens"] is None
    assert metadata["cost_usd"] is None
    # Sí están: provider_id resuelto del registry y latency_ms medido
    assert metadata["provider_id"] == "anthropic"
    assert metadata["latency_ms"] >= 0
    assert metadata["operation_id"]  # uuid generado por fallback


def test_metadata_schema_validates(
    make_client, fake_extractor_with_metadata, minimal_pdf_bytes
):
    """El bloque metadata debe pasar validación contra ``ExtractionMetadata``."""
    from sica_api.schemas import ExtractionMetadata

    client = make_client(extractor=fake_extractor_with_metadata)
    response = client.post(
        "/extract",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    metadata = response.json()["metadata"]
    # Si esto falla, hay un campo extra o un tipo incorrecto en el dict
    # construido por _build_response_metadata.
    parsed = ExtractionMetadata.model_validate(metadata)
    assert parsed.success is True
    assert parsed.model_used == "claude-sonnet-4-5-20250929"
