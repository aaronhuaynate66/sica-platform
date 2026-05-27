"""Tests unitarios del clinical-extractor.

Estos tests NO consumen la API de Anthropic — son unit tests puros.
Tests de integración (que sí llaman al modelo) se marcan con @pytest.mark.integration
y se corren manualmente con `pytest -m integration` cuando ANTHROPIC_API_KEY está disponible.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from clinical_extractor import extract_from_pdf
from clinical_extractor.extractor import ExtractionError, _build_extraction_tool
from clinical_extractor.prompts import (
    ACTIVE_PROMPT_VERSION,
    PROMPT_REGISTRY,
    get_active_prompt,
    get_prompt,
)
from clinical_extractor.schemas import EvidenceSpan, LabResult, ObstetricSummary

if TYPE_CHECKING:
    from pathlib import Path

# =========================================================================
# Schemas — validan que los modelos Pydantic se comportan como se espera
# =========================================================================


class TestObstetricSummarySchema:
    def test_can_instantiate_with_only_required_fields(self) -> None:
        summary = ObstetricSummary(confidence_score=0.5)
        assert summary.patient_age is None
        assert summary.gestational_age_weeks is None
        assert summary.active_problems == []
        assert summary.lab_results == []
        assert summary.evidence_spans == []
        assert summary.notes_summary == ""

    def test_confidence_score_must_be_between_0_and_1(self) -> None:
        with pytest.raises(ValidationError):
            ObstetricSummary(confidence_score=1.5)
        with pytest.raises(ValidationError):
            ObstetricSummary(confidence_score=-0.1)

    def test_patient_age_outside_human_range_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ObstetricSummary(confidence_score=0.5, patient_age=5)
        with pytest.raises(ValidationError):
            ObstetricSummary(confidence_score=0.5, patient_age=120)

    def test_gestational_age_weeks_bounds(self) -> None:
        ObstetricSummary(confidence_score=0.5, gestational_age_weeks=28.3)
        with pytest.raises(ValidationError):
            ObstetricSummary(confidence_score=0.5, gestational_age_weeks=-1)
        with pytest.raises(ValidationError):
            ObstetricSummary(confidence_score=0.5, gestational_age_weeks=50)

    def test_extra_fields_forbidden(self) -> None:
        """El schema rechaza campos extra — defensa contra modelos creativos."""
        with pytest.raises(ValidationError):
            ObstetricSummary.model_validate(
                {"confidence_score": 0.5, "campo_inventado": "valor"}
            )

    def test_full_example_roundtrip(self) -> None:
        summary = ObstetricSummary(
            patient_age=32,
            gestational_age_weeks=28.3,
            fum=date(2025, 9, 15),
            fpp=date(2026, 6, 22),
            active_problems=["Anemia leve en gestación previa"],
            risk_factors=["Cesárea previa", "G2P1"],
            lab_results=[
                LabResult(name="Hemoglobina", value="10.8", unit="g/dL", abnormal=True),
            ],
            notes_summary="Gestante de 28 semanas con antecedente de cesárea previa.",
            confidence_score=0.87,
            evidence_spans=[
                EvidenceSpan(
                    claim="Hb 10.8 g/dL",
                    source_page=2,
                    source_text="Hemoglobina: 10.8 g/dL",
                ),
            ],
        )
        dumped = summary.model_dump(mode="json")
        restored = ObstetricSummary.model_validate(dumped)
        assert restored == summary


class TestLabResultSchema:
    def test_minimal_lab_result(self) -> None:
        lab = LabResult(name="HIV", value="No reactivo")
        assert lab.unit is None
        assert lab.date is None
        assert lab.abnormal is None

    def test_lab_with_all_fields(self) -> None:
        lab = LabResult(
            name="Glucosa basal",
            value="92",
            unit="mg/dL",
            date=date(2026, 4, 10),
            abnormal=False,
        )
        assert lab.unit == "mg/dL"


class TestEvidenceSpanSchema:
    def test_source_page_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            EvidenceSpan(claim="x", source_page=0, source_text="y")

    def test_source_text_must_be_non_empty(self) -> None:
        with pytest.raises(ValidationError):
            EvidenceSpan(claim="x", source_page=1, source_text="")


# =========================================================================
# Prompts — registry y versionado
# =========================================================================


class TestPromptRegistry:
    def test_active_prompt_exists(self) -> None:
        active = get_active_prompt()
        assert active.version == ACTIVE_PROMPT_VERSION
        assert len(active.system) > 100  # prompt sustancial, no stub
        assert "{document_text}" in active.user_template

    def test_active_prompt_in_registry(self) -> None:
        assert ACTIVE_PROMPT_VERSION in PROMPT_REGISTRY

    def test_get_prompt_unknown_version_raises(self) -> None:
        with pytest.raises(KeyError, match="no existe"):
            get_prompt("999.999.999")

    def test_prompt_emphasizes_no_invention(self) -> None:
        """El prompt activo debe instruir explícitamente a no inventar."""
        active = get_active_prompt()
        # No es test exhaustivo; es smoke check de que las reglas críticas siguen ahí.
        assert "NO INVENTAR" in active.system or "no invent" in active.system.lower()


# =========================================================================
# Extractor — comportamiento ante PDFs inválidos (sin tocar API)
# =========================================================================


class TestExtractorErrorHandling:
    def test_missing_pdf_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ExtractionError, match="no existe"):
            extract_from_pdf(tmp_path / "no_existe.pdf")

    def test_non_pdf_extension_raises(self, tmp_path: Path) -> None:
        fake = tmp_path / "file.txt"
        fake.write_text("not a pdf")
        with pytest.raises(ExtractionError, match="no es PDF"):
            extract_from_pdf(fake)

    def test_extraction_tool_spec_uses_summary_schema(self) -> None:
        """El tool_spec entregado a Anthropic debe basarse en ObstetricSummary."""
        tool = _build_extraction_tool()
        assert tool["name"] == "record_obstetric_summary"
        schema = tool["input_schema"]
        assert "properties" in schema
        assert "confidence_score" in schema["properties"]
        assert "evidence_spans" in schema["properties"]

    def test_extractor_uses_injected_client_without_network(self, tmp_path: Path) -> None:
        """Inyectar un client mockeado evita llamadas reales y devuelve datos válidos."""
        # PDF dummy — pero pypdf necesita un PDF real, así que solo verificamos
        # que la lógica de fallback con client inyectado funciona si el PDF se lee.
        # Para mantener el test puro, usamos un PDF mínimo válido inline.
        pdf_bytes = _minimal_valid_pdf_bytes()
        pdf_path = tmp_path / "synthetic.pdf"
        pdf_path.write_bytes(pdf_bytes)

        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.name = "record_obstetric_summary"
        mock_block.input = {
            "confidence_score": 0.42,
            "active_problems": [],
            "risk_factors": [],
            "lab_results": [],
            "evidence_spans": [],
            "notes_summary": "",
        }
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        result = extract_from_pdf(pdf_path, client=mock_client)
        assert isinstance(result, ObstetricSummary)
        assert result.confidence_score == pytest.approx(0.42)
        mock_client.messages.create.assert_called_once()


class TestExtractorProviderRouting:
    """Resolución por ``provider_id`` desde el caller (e.g. apps/api)."""

    def test_unknown_provider_id_raises_extraction_error(self, tmp_path: Path) -> None:
        """provider_id no registrado → ExtractionError con detalle de disponibles."""
        pdf_path = tmp_path / "x.pdf"
        pdf_path.write_bytes(_minimal_valid_pdf_bytes())
        with pytest.raises(ExtractionError, match="no registrado"):
            extract_from_pdf(pdf_path, provider_id="openai")

    def test_provider_id_anthropic_resolves_anthropic_provider(
        self, tmp_path: Path
    ) -> None:
        """provider_id='anthropic' (con client inyectado) sigue funcionando."""
        pdf_path = tmp_path / "x.pdf"
        pdf_path.write_bytes(_minimal_valid_pdf_bytes())

        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.name = "record_obstetric_summary"
        mock_block.input = {
            "confidence_score": 0.5,
            "active_problems": [],
            "risk_factors": [],
            "lab_results": [],
            "evidence_spans": [],
            "notes_summary": "",
        }
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        # client inyectado: precedencia sobre provider_id, pero el resultado
        # equivale a usar anthropic.
        result = extract_from_pdf(pdf_path, client=mock_client, provider_id="anthropic")
        assert isinstance(result, ObstetricSummary)


# =========================================================================
# Helpers
# =========================================================================


def _minimal_valid_pdf_bytes() -> bytes:
    """PDF mínimo válido con una línea de texto extraíble, sin metadata."""
    # PDF estructuralmente válido con un Tj que pypdf puede leer.
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
