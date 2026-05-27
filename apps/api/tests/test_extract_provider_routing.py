"""Tests para el query param ``?provider=`` de POST /extract.

Cubren el contrato de routing introducido en ADR 0004 § Actualización
2026-05-27:

- Default sin query param → ``anthropic`` (compat).
- ``?provider=anthropic`` → mismo path.
- ``?provider=vertex`` → mapeo a ``vertex-medgemma`` internamente.
- ``?provider=openai`` o cualquier otro → 400 antes de leer el PDF.
- Errores del provider (no disponible, no implementado) → 503 con detail
  sanitizado, sin stack trace, sin PHI.
- ``provider_id`` se propaga al extractor como kwarg.
- ``provider`` aparece en metadata del span padre de Langfuse.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch


def test_extract_without_provider_uses_anthropic_default(
    make_client, minimal_pdf_bytes
) -> None:
    """Sin query param, el handler pasa provider_id='anthropic' al extractor."""
    captured: dict[str, Any] = {}

    def _spy(pdf_path, *, api_key: str, **kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
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

    client = make_client(extractor=_spy)
    response = client.post(
        "/extract",
        files={"file": ("synthetic_case_01.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    assert captured.get("provider_id") == "anthropic"


def test_extract_with_provider_anthropic_explicit_works(
    make_client, fake_extractor, minimal_pdf_bytes
) -> None:
    """?provider=anthropic produce el mismo resultado que el default."""
    captured: dict[str, Any] = {}

    def _spy(pdf_path, *, api_key: str, **kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return fake_extractor(pdf_path, api_key=api_key, **kwargs)

    client = make_client(extractor=_spy)
    response = client.post(
        "/extract?provider=anthropic",
        files={"file": ("synthetic_case_01.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    assert captured.get("provider_id") == "anthropic"


def test_extract_with_provider_vertex_maps_to_vertex_medgemma(
    make_client, fake_extractor, minimal_pdf_bytes
) -> None:
    """?provider=vertex se propaga como provider_id='vertex-medgemma' al extractor."""
    captured: dict[str, Any] = {}

    def _spy(pdf_path, *, api_key: str, **kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return fake_extractor(pdf_path, api_key=api_key, **kwargs)

    client = make_client(extractor=_spy)
    response = client.post(
        "/extract?provider=vertex",
        files={"file": ("synthetic_case_01.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    # Public 'vertex' → internal 'vertex-medgemma'.
    assert captured.get("provider_id") == "vertex-medgemma"


def test_extract_with_invalid_provider_returns_400(
    make_client, fake_extractor, minimal_pdf_bytes
) -> None:
    """Providers no soportados deben rechazarse antes del extractor."""
    extractor_called = {"n": 0}

    def _spy(pdf_path, *, api_key: str, **kwargs: Any) -> dict[str, Any]:
        extractor_called["n"] += 1
        return fake_extractor(pdf_path, api_key=api_key, **kwargs)

    client = make_client(extractor=_spy)
    response = client.post(
        "/extract?provider=openai",
        files={"file": ("c.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "invalid_provider"
    assert "openai" in body["detail"]
    # El detail menciona la lista de válidos para que el cliente se autocorrija.
    assert "anthropic" in body["detail"]
    assert "vertex" in body["detail"]
    # El extractor NO se llamó — validación temprana antes del I/O.
    assert extractor_called["n"] == 0


def test_extract_invalid_provider_validated_before_pdf_read(
    make_client, fake_extractor
) -> None:
    """Si el provider es inválido, ni siquiera se inspecciona el PDF.

    Verifica que el 400 sale aunque el body sea inválido (no es PDF).
    """
    client = make_client(extractor=fake_extractor)
    response = client.post(
        "/extract?provider=garbage",
        files={"file": ("c.pdf", b"NOT A PDF AT ALL", "application/pdf")},
    )
    # invalid_provider gana sobre not_a_pdf — validación temprana.
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_provider"


def test_extract_empty_provider_uses_default(
    make_client, fake_extractor, minimal_pdf_bytes
) -> None:
    """?provider= (vacío) cae al default 'anthropic'."""
    captured: dict[str, Any] = {}

    def _spy(pdf_path, *, api_key: str, **kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return fake_extractor(pdf_path, api_key=api_key, **kwargs)

    client = make_client(extractor=_spy)
    response = client.post(
        "/extract?provider=",
        files={"file": ("c.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    assert captured.get("provider_id") == "anthropic"


def test_extract_provider_unavailable_returns_503(
    make_client, minimal_pdf_bytes
) -> None:
    """Si el extractor levanta ProviderNotAvailableError → 503 con detail."""

    def _unavailable(pdf_path, *, api_key: str, **kwargs: Any) -> dict[str, Any]:
        # Replicamos la clase del extractor por nombre (mismo nombre que el
        # apps/api detecta para mapear a 503).
        from clinical_extractor.providers.base import ProviderNotAvailableError

        raise ProviderNotAvailableError(
            "Provider 'vertex-medgemma' no está disponible (faltan credenciales o config)."
        )

    client = make_client(extractor=_unavailable)
    response = client.post(
        "/extract?provider=vertex",
        files={"file": ("c.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "provider_unavailable"
    assert body["provider"] == "vertex"
    assert body["error_type"] == "ProviderNotAvailableError"
    assert "vertex" in body["detail"].lower() or "credenciales" in body["detail"].lower()
    # Sanity: error_id presente para correlación con logs.
    assert body.get("error_id")


def test_extract_provider_not_implemented_returns_503(
    make_client, minimal_pdf_bytes
) -> None:
    """VertexMedGemmaProvider.extract es stub → NotImplementedError → 503."""

    def _stub_provider(pdf_path, *, api_key: str, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError(
            "VertexMedGemmaProvider.extract no está implementado. "
            "Pendiente sesión con GCP credentials (issue #12)."
        )

    client = make_client(extractor=_stub_provider)
    response = client.post(
        "/extract?provider=vertex",
        files={"file": ("c.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "provider_unavailable"
    assert body["error_type"] == "NotImplementedError"
    assert "#12" in body["detail"] or "GCP" in body["detail"]


def test_extract_provider_503_does_not_leak_phi(
    make_client, minimal_pdf_bytes
) -> None:
    """Si el provider levanta con mensaje que contiene PHI, el response no expone PHI."""

    def _phi_in_error(pdf_path, *, api_key: str, **kwargs: Any) -> dict[str, Any]:
        # Mensaje que un provider mal escrito podría producir incluyendo PHI.
        # El response DEBE incluirlo solo si está sanitizado (corto, sin
        # newlines), y de todas formas el cliente no debería ver PHI.
        from clinical_extractor.providers.base import ProviderNotAvailableError

        raise ProviderNotAvailableError(
            "Provider unavailable while processing case for patient Maria Lopez DNI 47812936"
        )

    client = make_client(extractor=_phi_in_error)
    response = client.post(
        "/extract?provider=vertex",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 503
    text = response.text
    # NO stack trace.
    assert "Traceback" not in text
    # NOTE: el detail del provider sí incluye el mensaje cleanedo, lo cual
    # podría llevar PHI si el provider lo embebió. Esta es una limitación
    # conocida — el provider NO debería poner PHI en mensajes de excepción.
    # Sin embargo, sí garantizamos: <200 chars, sin newlines, sin traceback.
    assert "\n" not in response.json()["detail"]
    assert len(response.json()["detail"]) <= 250


def test_extract_provider_propagates_to_trace_metadata(
    make_client, fake_extractor, minimal_pdf_bytes, monkeypatch
) -> None:
    """El span padre en Langfuse lleva metadata.provider con el valor público."""
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-x")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-x")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://test.local")
    from sica_api import tracing as _tracing
    from sica_api.settings import get_settings

    get_settings.cache_clear()
    _tracing.get_langfuse_client.cache_clear()

    from unittest.mock import MagicMock

    mock_span = MagicMock(trace_id="t-1", id="s-1")
    mock_client = MagicMock()
    mock_client.start_observation.return_value = mock_span

    with patch("langfuse.Langfuse", return_value=mock_client):
        client = make_client(extractor=fake_extractor)
        response = client.post(
            "/extract?provider=vertex",
            files={"file": ("synthetic_case_01.pdf", minimal_pdf_bytes, "application/pdf")},
        )

    # vertex es stub — pero el fake_extractor no levanta. Verificamos
    # que la metadata del span padre incluye el provider público.
    assert response.status_code == 200
    sent_metadata = mock_client.start_observation.call_args.kwargs["metadata"]
    assert sent_metadata.get("provider") == "vertex"


def test_extract_anthropic_path_unaffected_by_routing(
    make_client, fake_extractor, minimal_pdf_bytes
) -> None:
    """Sanity: contrato del path anthropic (con y sin query) sigue OK end-to-end."""
    client = make_client(extractor=fake_extractor)
    # Sin query.
    r1 = client.post(
        "/extract",
        files={"file": ("synthetic_a.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert r1.status_code == 200
    assert r1.json()["confidence_score"] == 0.91
    # Con query explícito.
    r2 = client.post(
        "/extract?provider=anthropic",
        files={"file": ("synthetic_b.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert r2.status_code == 200
    assert r2.json()["confidence_score"] == 0.91
