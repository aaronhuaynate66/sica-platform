"""Tests para POST /extract."""

from __future__ import annotations


def test_extract_valid_pdf_returns_200(make_client, fake_extractor, minimal_pdf_bytes):
    client = make_client(extractor=fake_extractor)
    response = client.post(
        "/extract",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["patient_age"] == 32
    assert "confidence_score" in body
    assert "X-Request-ID" in response.headers


def test_extract_without_file_returns_422(make_client, fake_extractor):
    client = make_client(extractor=fake_extractor)
    response = client.post("/extract")
    assert response.status_code == 422


def test_extract_non_pdf_content_type_returns_400(make_client, fake_extractor):
    client = make_client(extractor=fake_extractor)
    response = client.post(
        "/extract",
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "not_a_pdf"


def test_extract_wrong_magic_bytes_returns_400(make_client, fake_extractor):
    """Content-type lying as application/pdf, body is not actually a PDF."""
    client = make_client(extractor=fake_extractor)
    response = client.post(
        "/extract",
        files={"file": ("fake.pdf", b"NOT A PDF AT ALL", "application/pdf")},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "not_a_pdf"


def test_extract_file_too_large_returns_413(make_client, fake_extractor):
    """Set max_mb=1 and upload 2MB to trigger the size guard."""
    client = make_client(extractor=fake_extractor, max_mb=1)
    big = b"%PDF-1.4\n" + (b"x" * (2 * 1024 * 1024))
    response = client.post(
        "/extract",
        files={"file": ("big.pdf", big, "application/pdf")},
    )
    assert response.status_code == 413
    assert response.json()["error"] == "file_too_large"


def test_extract_missing_api_key_returns_503(make_client, fake_extractor, minimal_pdf_bytes):
    client = make_client(api_key=None, extractor=fake_extractor)
    response = client.post(
        "/extract",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "extractor_unavailable"
    assert "request_id" in body


def test_extract_extractor_failure_returns_500_with_error_id(
    make_client, failing_extractor, minimal_pdf_bytes
):
    client = make_client(extractor=failing_extractor)
    response = client.post(
        "/extract",
        files={"file": ("synthetic.pdf", minimal_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "extraction_failed"
    assert body["error_id"] is not None
    # Stack trace must NOT leak into the response.
    payload = response.text
    assert "Traceback" not in payload
    assert "simulated extractor failure" not in payload


def test_extract_empty_file_returns_400(make_client, fake_extractor):
    client = make_client(extractor=fake_extractor)
    response = client.post(
        "/extract",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "empty_file"


def test_extract_propagates_request_id_in_error_response(
    make_client, fake_extractor
):
    """An error response must still carry X-Request-ID and the body must echo it."""
    client = make_client(extractor=fake_extractor)
    response = client.post(
        "/extract",
        files={"file": ("notes.txt", b"hi", "text/plain")},
        headers={"X-Request-ID": "deadbeef-1234"},
    )
    assert response.status_code == 400
    assert response.headers.get("X-Request-ID") == "deadbeef-1234"
    assert response.json()["request_id"] == "deadbeef-1234"
