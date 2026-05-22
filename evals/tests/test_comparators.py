"""Tests for sica_evals.comparators."""

from __future__ import annotations

from sica_evals.comparators.field_comparator import (
    CRITICAL_FIELDS,
    compare_obstetric_summary,
)
from sica_evals.comparators.span_comparator import (
    compare_evidence_spans,
    span_in_text,
)


def _perfect_summary() -> dict:
    """Minimal expected/actual dict that should yield perfect comparisons."""
    return {
        "patient_age": 32,
        "gestational_age_weeks": 28.3,
        "fum": "2025-09-15",
        "fpp": "2026-06-22",
        "active_problems": ["Anemia leve gestacional"],
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
        "notes_summary": "Paciente de 32 años, gestación 28 semanas.",
        "confidence_score": 0.95,
        "evidence_spans": [],
    }


def test_compare_identical_summaries_all_match() -> None:
    summary = _perfect_summary()
    comparisons = compare_obstetric_summary(summary, summary)
    assert all(c.match for c in comparisons)
    assert {c.field_name for c in comparisons} >= {
        "patient_age",
        "gestational_age_weeks",
        "fum",
        "fpp",
        "active_problems",
        "risk_factors",
        "notes_summary",
    }


def test_gestational_age_tolerance_within_threshold() -> None:
    a = _perfect_summary()
    b = _perfect_summary()
    b["gestational_age_weeks"] = 28.5  # within ±0.5
    comparisons = compare_obstetric_summary(a, b)
    ga = next(c for c in comparisons if c.field_name == "gestational_age_weeks")
    assert ga.match is True
    assert ga.match_type == "fuzzy"


def test_gestational_age_outside_threshold() -> None:
    a = _perfect_summary()
    b = _perfect_summary()
    b["gestational_age_weeks"] = 30.0  # delta 1.7 > 0.5
    comparisons = compare_obstetric_summary(a, b)
    ga = next(c for c in comparisons if c.field_name == "gestational_age_weeks")
    assert ga.match is False
    assert ga.match_type == "mismatch"


def test_missing_value_is_flagged_missing() -> None:
    a = _perfect_summary()
    b = _perfect_summary()
    b["patient_age"] = None
    comparisons = compare_obstetric_summary(a, b)
    cmp_age = next(c for c in comparisons if c.field_name == "patient_age")
    assert cmp_age.match is False
    assert cmp_age.match_type == "missing"
    assert cmp_age.weight == 2.0  # critical


def test_hallucinated_value_is_flagged_hallucinated() -> None:
    a = _perfect_summary()
    b = _perfect_summary()
    a["patient_age"] = None  # expected None
    b["patient_age"] = 32
    comparisons = compare_obstetric_summary(a, b)
    cmp_age = next(c for c in comparisons if c.field_name == "patient_age")
    assert cmp_age.match is False
    assert cmp_age.match_type == "hallucinated"


def test_critical_field_weights() -> None:
    summary = _perfect_summary()
    comparisons = compare_obstetric_summary(summary, summary)
    for c in comparisons:
        base = c.field_name.split("[")[0].split(".")[0]
        if base in CRITICAL_FIELDS:
            assert c.weight == 2.0, f"{c.field_name} should be critical"


def test_lab_results_match_by_name() -> None:
    a = _perfect_summary()
    b = _perfect_summary()
    # Reorder the labs to ensure matching is name-based, not positional.
    b["lab_results"] = list(reversed(a["lab_results"]))
    comparisons = compare_obstetric_summary(a, b)
    lab_cmps = [c for c in comparisons if c.field_name.startswith("lab_results[")]
    assert lab_cmps, "expected at least one lab comparison"
    assert all(c.match for c in lab_cmps)


def test_missing_abnormal_lab_is_critical() -> None:
    a = _perfect_summary()
    b = _perfect_summary()
    b["lab_results"] = []  # whole list missing
    comparisons = compare_obstetric_summary(a, b)
    missing_critical = [
        c for c in comparisons
        if c.field_name.startswith("lab_results[") and c.match_type == "missing"
    ]
    assert missing_critical, "expected at least one missing lab comparison"
    # Hemoglobina with abnormal=True should produce a 2.0-weight missing record.
    assert any(c.weight == 2.0 for c in missing_critical)


def test_fuzzy_problem_list_matches_with_minor_diff() -> None:
    a = _perfect_summary()
    b = _perfect_summary()
    b["active_problems"] = ["Anemia leve gestacional confirmada"]  # extra suffix
    comparisons = compare_obstetric_summary(a, b)
    cmp = next(c for c in comparisons if c.field_name == "active_problems")
    # Should be considered a fuzzy match given the high token overlap.
    assert cmp.confidence >= 0.6
    assert cmp.match_type in {"fuzzy", "exact"}


def test_notes_summary_completely_different_fails() -> None:
    a = _perfect_summary()
    b = _perfect_summary()
    b["notes_summary"] = "Texto completamente distinto sin nada en común"
    comparisons = compare_obstetric_summary(a, b)
    cmp = next(c for c in comparisons if c.field_name == "notes_summary")
    assert cmp.match is False
    assert cmp.match_type == "mismatch"


def test_span_in_text_substring_present() -> None:
    pdf_text = "Edad: 32 años\nFUM: 15/09/2025\nDiagnóstico: anemia gestacional leve"
    assert span_in_text("FUM: 15/09/2025", pdf_text) is True
    assert span_in_text("Inexistente literal del paciente", pdf_text) is False


def test_span_in_text_pdf_none_is_conservative() -> None:
    # When PDF text is unavailable, span_in_text returns True conservatively.
    assert span_in_text("any text", None) is True


def test_compare_evidence_spans_detects_hallucination() -> None:
    pdf_text = "Edad: 32 años\nFUM: 15/09/2025"
    expected = [{"claim": "Edad 32 años", "source_page": 1, "source_text": "Edad: 32 años"}]
    actual = [
        {"claim": "Edad 32 años", "source_page": 1, "source_text": "Edad: 32 años"},
        # Hallucinated: claim not in expected and text not in pdf.
        {"claim": "Cesárea previa", "source_page": 1, "source_text": "Antecedente de cesárea 2020"},
    ]
    comparisons = compare_evidence_spans(expected, actual, pdf_text=pdf_text)
    halluc = [c for c in comparisons if c.match_type == "hallucinated"]
    assert len(halluc) == 1
    assert halluc[0].field_name.startswith("evidence_spans[+")
