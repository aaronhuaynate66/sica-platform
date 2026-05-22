"""Tests for sica_evals.harness end-to-end with MockExtractor."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sica_evals.extractors import MockExtractor
from sica_evals.harness import Harness, diff_reports
from sica_evals.schemas import HarnessReport


@pytest.fixture
def fixtures_tmp(tmp_path: Path) -> Path:
    """Build a fixtures dir with one expected case for the harness to load."""
    expected = {
        "patient_age": 32,
        "gestational_age_weeks": 28.3,
        "fum": "2025-09-15",
        "fpp": "2026-06-22",
        "active_problems": ["Anemia leve"],
        "risk_factors": ["Cesárea previa"],
        "lab_results": [
            {
                "name": "Hemoglobina",
                "value": "10.8",
                "unit": "g/dL",
                "date": "2026-04-02",
                "abnormal": True,
            }
        ],
        "notes_summary": "Resumen narrativo.",
        "confidence_score": 0.95,
        "evidence_spans": [],
    }
    pdf_path = tmp_path / "case_a.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock")
    (tmp_path / "case_a.expected.json").write_text(
        json.dumps(expected), encoding="utf-8"
    )
    (tmp_path / "case_a.expected.meta.json").write_text(
        json.dumps(
            {
                "pdf_source": {"path": str(pdf_path)},
                "baseline_type": "synthetic",
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_load_test_cases_picks_up_fixture(fixtures_tmp: Path, tmp_path: Path) -> None:
    mock = MockExtractor()
    harness = Harness(mock, fixtures_dir=fixtures_tmp, output_dir=tmp_path / "out")
    cases = harness.load_test_cases()
    assert len(cases) == 1
    assert cases[0].case_id == "case_a"


def test_run_all_with_perfect_mock(fixtures_tmp: Path, tmp_path: Path) -> None:
    """When the mock returns exactly the expected dict, accuracy should be 1.0."""
    expected = json.loads((fixtures_tmp / "case_a.expected.json").read_text())
    pdf_path = fixtures_tmp / "case_a.pdf"
    mock = MockExtractor({pdf_path: expected})

    harness = Harness(
        mock,
        fixtures_dir=fixtures_tmp,
        output_dir=tmp_path / "out",
        extractor_version="mock-test",
        model_used="mock",
    )
    report = harness.run_all()
    assert report.cases_total == 1
    assert report.cases_succeeded == 1
    assert report.cases_failed == 0
    assert report.aggregate_metrics["factual_accuracy_mean"] == 1.0
    assert report.aggregate_metrics["critical_omissions_total"] == 0.0
    assert report.aggregate_metrics["hallucinations_total"] == 0.0


def test_run_all_writes_all_three_formats(
    fixtures_tmp: Path, tmp_path: Path
) -> None:
    expected = json.loads((fixtures_tmp / "case_a.expected.json").read_text())
    pdf_path = fixtures_tmp / "case_a.pdf"
    mock = MockExtractor({pdf_path: expected})

    out = tmp_path / "out"
    harness = Harness(mock, fixtures_dir=fixtures_tmp, output_dir=out)
    report = harness.run_all()
    written = harness.save_report(report, formats=("json", "markdown", "html"))
    assert {"json", "markdown", "html"} == set(written)
    for path in written.values():
        assert path.exists()
        assert path.stat().st_size > 0


def test_run_all_handles_extractor_exception(
    fixtures_tmp: Path, tmp_path: Path
) -> None:
    """Extractor raises => case has error set, metrics zeroed."""

    def failing(_: Path) -> dict:
        msg = "boom"
        raise RuntimeError(msg)

    harness = Harness(failing, fixtures_dir=fixtures_tmp, output_dir=tmp_path / "out")
    report = harness.run_all()
    assert report.cases_failed == 1
    assert report.cases_succeeded == 0
    r = report.per_case_results[0]
    assert r.error is not None and "boom" in r.error
    assert r.factual_accuracy == 0.0


def test_diff_reports_detects_regression(
    fixtures_tmp: Path, tmp_path: Path
) -> None:
    expected = json.loads((fixtures_tmp / "case_a.expected.json").read_text())
    pdf_path = fixtures_tmp / "case_a.pdf"

    # Report A: perfect
    mock_perfect = MockExtractor({pdf_path: expected})
    harness_a = Harness(mock_perfect, fixtures_dir=fixtures_tmp, output_dir=tmp_path / "a")
    report_a = harness_a.run_all()

    # Report B: regressed — drop patient_age
    regressed = {**expected, "patient_age": None}
    mock_regressed = MockExtractor({pdf_path: regressed})
    harness_b = Harness(mock_regressed, fixtures_dir=fixtures_tmp, output_dir=tmp_path / "b")
    report_b = harness_b.run_all()

    delta = diff_reports(report_a, report_b)
    assert delta["aggregate_delta"]["factual_accuracy_mean"] < 0
    assert delta["aggregate_delta"]["critical_omissions_total"] >= 1


def test_report_serializes_to_json_and_back(
    fixtures_tmp: Path, tmp_path: Path
) -> None:
    expected = json.loads((fixtures_tmp / "case_a.expected.json").read_text())
    pdf_path = fixtures_tmp / "case_a.pdf"
    mock = MockExtractor({pdf_path: expected})
    harness = Harness(mock, fixtures_dir=fixtures_tmp, output_dir=tmp_path / "out")
    report = harness.run_all()
    written = harness.save_report(report, formats=("json",))
    payload = json.loads(written["json"].read_text(encoding="utf-8"))
    rehydrated = HarnessReport.model_validate(payload)
    assert rehydrated.run_id == report.run_id
    assert rehydrated.aggregate_metrics == report.aggregate_metrics
