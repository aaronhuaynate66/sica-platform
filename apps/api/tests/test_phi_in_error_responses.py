"""Tests del helper ``_safe_provider_error_detail`` y la redacción PHI en
los responses de error del handler ``POST /extract``.

Cubre el cierre del TODO #6 del adapter pattern (sesión 2026-05-27): los
mensajes de excepción del provider pueden traer PHI inline; el response al
cliente debe quedar sanitizado antes de salir.

Política: ADR-0009 (redacción inline de DNI peruano 8-dig, móvil 9-dig,
email) más el pipeline existente del helper (colapsar whitespace, truncar
a 200 chars, fallback genérico para mensajes vacíos).
"""

from __future__ import annotations

from typing import Any

from sica_api.routes.extract import _safe_provider_error_detail

# =========================================================================
# Helper unit tests — _safe_provider_error_detail
# =========================================================================


def test_helper_redacts_dni_inline() -> None:
    """DNI peruano (8 dígitos) inline en el mensaje de excepción se redacta."""

    class _FakeExc(Exception):
        pass

    exc = _FakeExc("Failed for DNI 47812936 in provider call")
    detail = _safe_provider_error_detail(exc)
    assert "[REDACTED]" in detail
    assert "47812936" not in detail


def test_helper_redacts_email_inline() -> None:
    """Email inline se redacta."""

    class _FakeExc(Exception):
        pass

    exc = _FakeExc("Notification failed for user maria@test.com")
    detail = _safe_provider_error_detail(exc)
    assert "[REDACTED]" in detail
    assert "maria@test.com" not in detail


def test_helper_redacts_peruvian_mobile_inline() -> None:
    """Móvil peruano (9 dígitos, prefijo 9) inline se redacta."""

    class _FakeExc(Exception):
        pass

    exc = _FakeExc("contact telefono 987654321 unreachable")
    detail = _safe_provider_error_detail(exc)
    assert "[REDACTED]" in detail
    assert "987654321" not in detail


def test_helper_preserves_non_phi_messages() -> None:
    """Mensajes sin PHI pasan tal cual (modulo whitespace collapse)."""

    class _FakeExc(Exception):
        pass

    exc = _FakeExc("Provider unavailable: stub not wired to GCP yet")
    detail = _safe_provider_error_detail(exc)
    assert "Provider unavailable" in detail
    assert "stub not wired" in detail
    assert "GCP" in detail
    assert "[REDACTED]" not in detail


def test_helper_truncates_to_200_chars() -> None:
    """Mensajes largos se truncan a 200 chars."""

    class _FakeExc(Exception):
        pass

    long_msg = "Provider failed: " + ("a" * 500)
    exc = _FakeExc(long_msg)
    detail = _safe_provider_error_detail(exc)
    assert len(detail) <= 200


def test_helper_collapses_whitespace() -> None:
    """Saltos de línea y tabs se reemplazan por un único espacio."""

    class _FakeExc(Exception):
        pass

    exc = _FakeExc("line1\n\nline2\twith tabs\n\n\nline3")
    detail = _safe_provider_error_detail(exc)
    assert "\n" not in detail
    assert "\t" not in detail
    # Mensaje preservado en una sola línea.
    assert "line1 line2 with tabs line3" in detail


def test_helper_empty_message_returns_fallback() -> None:
    """Excepción sin mensaje (str(exc) == '') devuelve fallback genérico."""

    class _FakeExc(Exception):
        pass

    exc = _FakeExc("")
    detail = _safe_provider_error_detail(exc)
    assert detail  # no string vacío
    assert "[REDACTED]" not in detail  # no aplica redacción a fallback
    assert "no está disponible" in detail.lower() or "unavailable" in detail.lower()


def test_helper_combines_redaction_and_truncation() -> None:
    """PHI primero (redact) y luego truncate — el orden importa para no
    perder la redacción si el truncate corta justo en medio del DNI."""

    class _FakeExc(Exception):
        pass

    # DNI cerca del límite de 200 chars: si truncamos antes de redactar,
    # el final del DNI quedaría visible. El pipeline garantiza redacción
    # ANTES del truncate.
    long_with_phi = ("x" * 180) + " DNI 47812936 trailing"
    exc = _FakeExc(long_with_phi)
    detail = _safe_provider_error_detail(exc)
    assert "47812936" not in detail


# =========================================================================
# E2E via TestClient — el response al cliente queda redactado
# =========================================================================


def test_503_response_redacts_dni_in_provider_message(
    make_client, minimal_pdf_bytes
) -> None:
    """E2E: si el provider levanta una excepción con DNI inline, el response
    503 al cliente lleva [REDACTED] en lugar del DNI."""

    def _phi_in_error(pdf_path, *, api_key: str, **kwargs: Any) -> dict[str, Any]:
        from clinical_extractor.providers.base import ProviderNotAvailableError

        raise ProviderNotAvailableError(
            "Provider unavailable while processing case for patient DNI 47812936"
        )

    client = make_client(extractor=_phi_in_error)
    response = client.post(
        "/extract?provider=vertex",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 503
    body = response.json()
    # PHI no debe aparecer en el detail.
    assert "47812936" not in body["detail"]
    assert "[REDACTED]" in body["detail"]
    # El contexto del error sigue siendo legible.
    assert "vertex" in body["detail"].lower() or "provider" in body["detail"].lower()


def test_503_response_redacts_email_in_provider_message(
    make_client, minimal_pdf_bytes
) -> None:
    """E2E: email inline en mensaje de excepción → redactado en response."""

    def _phi_email(pdf_path, *, api_key: str, **kwargs: Any) -> dict[str, Any]:
        from clinical_extractor.providers.base import ProviderNotAvailableError

        raise ProviderNotAvailableError(
            "Notification to lucia.mendoza@example.com failed during retry"
        )

    client = make_client(extractor=_phi_email)
    response = client.post(
        "/extract?provider=vertex",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 503
    assert "lucia.mendoza@example.com" not in response.text
    assert "[REDACTED]" in response.json()["detail"]


def test_400_invalid_provider_redacts_user_echo(make_client, minimal_pdf_bytes) -> None:
    """E2E: si el cliente pone un DNI como ?provider=, el eco va redactado.

    Defensa contra reflected PHI: el query param se hace eco en el detail
    para auto-corrección del cliente, pero PHI inline (8 dígitos) se redacta.
    """
    client = make_client()
    response = client.post(
        "/extract?provider=47812936",  # 8 dígitos — match con pattern DNI
        files={"file": ("c.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 400
    body = response.json()
    assert "47812936" not in body["detail"]
    assert body["error"] == "invalid_provider"


def test_400_invalid_content_type_redacts_user_echo(make_client) -> None:
    """E2E: content-type echo va redactado si trae PHI inline."""
    client = make_client()
    response = client.post(
        "/extract",
        files={
            "file": (
                "notes.txt",
                b"hi",
                # content_type con DNI inline (caso patológico).
                "text/plain; phi=47812936",
            )
        },
    )
    assert response.status_code == 400
    body = response.json()
    assert "47812936" not in body["detail"]
    assert body["error"] == "not_a_pdf"


# =========================================================================
# Graceful degradation — si clinical_extractor.phi no estuviera disponible
# =========================================================================


def test_helper_redacts_key_in_text_pattern() -> None:
    """ADR-0009 actualización 2026-05-27: el helper redacta valores asociados
    a keys PHI cuando aparecen en texto plano dentro del mensaje de excepción.

    El sanitizer existente capturaba PHI inline (DNI / móvil / email), pero
    NO capturaba el patrón ``nombre=Maria`` cuando aparecía dentro de un
    string libre. Ahora sí.
    """

    class _FakeExc(Exception):
        pass

    exc = _FakeExc("Failed for nombre=Maria Lopez DNI 47812936 control")
    detail = _safe_provider_error_detail(exc)
    # "Maria Lopez" no debe aparecer (era PHI con key en texto).
    assert "Maria Lopez" not in detail
    # "47812936" tampoco (PHI inline).
    assert "47812936" not in detail
    # El contexto del error sigue siendo legible.
    assert "Failed for" in detail
    assert "control" in detail
    # Marcador presente al menos una vez.
    assert "[REDACTED]" in detail


def test_503_response_redacts_nombre_with_key_in_text(
    make_client, minimal_pdf_bytes
) -> None:
    """E2E: si el provider levanta una excepción con ``nombre=Maria Lopez`` en
    el mensaje, el response 503 al cliente NO contiene el nombre."""

    def _phi_provider(pdf_path, *, api_key: str, **kwargs: Any) -> dict[str, Any]:
        from clinical_extractor.providers.base import ProviderNotAvailableError

        raise ProviderNotAvailableError(
            "Failed for patient nombre=Maria Lopez DNI 47812936 control aborted"
        )

    client = make_client(extractor=_phi_provider)
    response = client.post(
        "/extract?provider=vertex",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 503
    body = response.json()
    # Ni el nombre ni el DNI deben aparecer.
    assert "Maria Lopez" not in body["detail"]
    assert "47812936" not in body["detail"]
    # El marcador y el contexto sí.
    assert "[REDACTED]" in body["detail"]


def test_helper_works_when_redactor_unavailable(monkeypatch) -> None:
    """Si el módulo PHI del extractor no se pudo importar, el helper degrada
    a sólo whitespace/truncate sin crashear."""
    from sica_api.routes import extract as extract_module

    monkeypatch.setattr(extract_module, "_redact_phi", None)
    monkeypatch.setattr(extract_module, "_redact_phi_available", False)

    class _FakeExc(Exception):
        pass

    # Sin redactor disponible, el DNI se preserva (degradación documentada).
    exc = _FakeExc("Failed for DNI 47812936")
    detail = extract_module._safe_provider_error_detail(exc)
    # El detail no crashea, devuelve string.
    assert isinstance(detail, str)
    assert detail  # no vacío
    # Sin redactor, el DNI puede pasar — el sistema sigue funcional.
    assert "47812936" in detail
