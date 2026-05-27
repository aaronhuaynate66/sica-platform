"""Tests del CLI del clinical-extractor.

Foco actual: el flag ``--prompt-version`` (ADR 0008, Fase 1+) que permite
forzar una versión específica del prompt desde la línea de comando.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from click.testing import CliRunner

from clinical_extractor.cli import cli

if TYPE_CHECKING:
    from pathlib import Path


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
        b"0000000050 00000 n \n"
        b"0000000089 00000 n \n"
        b"0000000160 00000 n \n"
        b"0000000220 00000 n \n"
        b"trailer<</Size 6/Root 1 0 R>>\n"
        b"startxref\n280\n%%EOF\n"
    )


def _mock_summary_payload() -> dict:
    """Payload válido para ObstetricSummary.model_validate."""
    return {
        "confidence_score": 0.88,
        "active_problems": [],
        "risk_factors": [],
        "lab_results": [],
        "evidence_spans": [],
        "notes_summary": "Test.",
        "patient_age": 30,
        "gestational_age_weeks": 24.0,
    }


def _patch_extractor_to_return_summary():
    """Devuelve un context manager que patch-ea extract_from_pdf para no
    llamar al provider real durante los tests del CLI.

    Importante: parcheamos en el módulo ``clinical_extractor.cli`` (donde
    el símbolo se importó), no en ``clinical_extractor.extractor`` (donde
    está definido).
    """
    from unittest.mock import MagicMock

    summary = MagicMock()
    summary.confidence_score = 0.88
    summary.evidence_spans = []
    summary.model_dump.return_value = _mock_summary_payload()
    return patch("clinical_extractor.cli.extract_from_pdf", return_value=summary)


def test_cli_without_prompt_version_uses_latest(tmp_path: Path) -> None:
    """Sin --prompt-version → log dice [latest] y kwarg llega como None."""
    pdf = tmp_path / "input.pdf"
    pdf.write_bytes(_minimal_valid_pdf_bytes())

    runner = CliRunner()
    with _patch_extractor_to_return_summary() as mock_extract:
        result = runner.invoke(cli, ["extract", str(pdf)])

    assert result.exit_code == 0, result.output
    # El log de stderr (capturado en .output por CliRunner) debe indicar latest.
    assert "[latest]" in result.output
    assert "[forced via CLI]" not in result.output
    # El extractor recibió prompt_version=None.
    mock_extract.assert_called_once()
    kwargs = mock_extract.call_args.kwargs
    assert kwargs.get("prompt_version") is None


def test_cli_with_prompt_version_passes_to_extractor(tmp_path: Path) -> None:
    """Con --prompt-version=1 → log dice [forced via CLI] y kwarg llega como 1."""
    pdf = tmp_path / "input.pdf"
    pdf.write_bytes(_minimal_valid_pdf_bytes())

    runner = CliRunner()
    with _patch_extractor_to_return_summary() as mock_extract:
        result = runner.invoke(cli, ["extract", str(pdf), "--prompt-version", "1"])

    assert result.exit_code == 0, result.output
    assert "[forced via CLI]" in result.output
    assert "[latest]" not in result.output
    # Hash visible en el log para auditoría.
    assert "hash=" in result.output
    mock_extract.assert_called_once()
    assert mock_extract.call_args.kwargs.get("prompt_version") == 1


def test_cli_with_nonexistent_prompt_version_fails_gracefully(tmp_path: Path) -> None:
    """--prompt-version=999 → exit code 1, mensaje legible, sin traceback."""
    pdf = tmp_path / "input.pdf"
    pdf.write_bytes(_minimal_valid_pdf_bytes())

    runner = CliRunner()
    # NO patcheamos extract_from_pdf — el CLI debe fallar ANTES de invocarlo,
    # en la resolución temprana del prompt.
    result = runner.invoke(cli, ["extract", str(pdf), "--prompt-version", "999"])

    assert result.exit_code == 1
    # Mensaje legible (sin Traceback).
    assert "Traceback" not in result.output
    assert "999" in result.output
    # Indica versiones disponibles para autoayuda.
    assert "Disponibles:" in result.output or "disponibles" in result.output.lower()


def test_cli_prompt_version_logs_short_hash(tmp_path: Path) -> None:
    """El log de prompt activo incluye los primeros 8 chars del hash."""
    pdf = tmp_path / "input.pdf"
    pdf.write_bytes(_minimal_valid_pdf_bytes())

    runner = CliRunner()
    with _patch_extractor_to_return_summary():
        result = runner.invoke(cli, ["extract", str(pdf)])

    assert result.exit_code == 0
    # Hash de extract_obstetric_v1 anclado en test_prompt_registry.
    # Verificamos que aparece un substring `hash=XXXXXXXX` con 8 chars hex.
    import re

    assert re.search(r"hash=[0-9a-f]{8}", result.output), result.output


def test_cli_help_shows_prompt_version_flag() -> None:
    """El --help del comando extract menciona --prompt-version."""
    runner = CliRunner()
    result = runner.invoke(cli, ["extract", "--help"])
    assert result.exit_code == 0
    assert "--prompt-version" in result.output
    # Hint sobre default y propósito.
    assert "latest" in result.output.lower() or "registry" in result.output.lower()
