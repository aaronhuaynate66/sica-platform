"""Tests for sica_evals.metrics."""

from __future__ import annotations

from datetime import UTC, datetime

from sica_evals.comparators.field_comparator import compare_obstetric_summary
from sica_evals.metrics import (
    compute_calibration_error,
    compute_factual_accuracy,
    count_critical_omissions,
    detect_hallucinations,
)
from sica_evals.metrics.factual_accuracy import compute_factual_accuracy_critical_only
from sica_evals.schemas import CaseResult, FieldComparison


def _perfect_summary() -> dict:
    return {
        "patient_age": 32,
        "gestational_age_weeks": 28.3,
        "fum": "2025-09-15",
        "fpp": "2026-06-22",
        "active_problems": ["Anemia leve"],
        "risk_factors": [],
        "lab_results": [],
        "notes_summary": "Resumen.",
    }


def test_factual_accuracy_perfect_is_one() -> None:
    summary = _perfect_summary()
    comparisons = compare_obstetric_summary(summary, summary)
    assert compute_factual_accuracy(comparisons) == 1.0


def test_factual_accuracy_empty_is_zero() -> None:
    assert compute_factual_accuracy([]) == 0.0


def test_factual_accuracy_handles_partial_mismatch() -> None:
    a = _perfect_summary()
    b = _perfect_summary()
    b["patient_age"] = 40  # wrong
    comparisons = compare_obstetric_summary(a, b)
    acc = compute_factual_accuracy(comparisons)
    assert 0.0 < acc < 1.0


def test_critical_only_accuracy_punishes_critical_misses() -> None:
    a = _perfect_summary()
    b = _perfect_summary()
    b["gestational_age_weeks"] = 35.0  # outside tolerance
    comparisons = compare_obstetric_summary(a, b)
    # Critical-only accuracy must drop when a critical field fails.
    crit_acc = compute_factual_accuracy_critical_only(comparisons)
    overall_acc = compute_factual_accuracy(comparisons)
    assert crit_acc < 1.0
    assert crit_acc <= overall_acc + 0.01  # critical penalty at least as harsh


def test_critical_omissions_detected() -> None:
    a = _perfect_summary()
    a["lab_results"] = [
        {
            "name": "Hemoglobina",
            "value": "10.8",
            "unit": "g/dL",
            "date": "2026-04-02",
            "abnormal": True,
        }
    ]
    b = _perfect_summary()  # missing the lab
    comparisons = compare_obstetric_summary(a, b)
    n = count_critical_omissions(comparisons)
    assert n >= 1  # at least the abnormal lab


def test_critical_omissions_zero_when_no_misses() -> None:
    summary = _perfect_summary()
    comparisons = compare_obstetric_summary(summary, summary)
    assert count_critical_omissions(comparisons) == 0


def test_hallucinations_detected_when_extra_field() -> None:
    a = _perfect_summary()
    b = _perfect_summary()
    a["patient_age"] = None  # expected absent
    b["patient_age"] = 32  # actual fabricated
    comparisons = compare_obstetric_summary(a, b)
    descriptions = detect_hallucinations(comparisons)
    assert len(descriptions) >= 1
    assert any("patient_age" in d for d in descriptions)


def test_hallucinations_empty_when_clean() -> None:
    summary = _perfect_summary()
    comparisons = compare_obstetric_summary(summary, summary)
    assert detect_hallucinations(comparisons) == []


def test_calibration_error_empty_returns_zero() -> None:
    assert compute_calibration_error([]) == 0.0


def test_calibration_error_perfectly_calibrated_is_zero() -> None:
    now = datetime.now(UTC)
    results = [
        CaseResult(
            case_id=f"c{i}",
            factual_accuracy=0.9,
            critical_omissions=0,
            hallucinations=0,
            confidence_calibration_error=0.0,  # |0.9 - 0.9|
            field_comparisons=[],
            hallucination_descriptions=[],
            timestamp=now,
        )
        for i in range(3)
    ]
    # All bucketed into the same bin, accuracy == confidence (since error=0).
    assert compute_calibration_error(results) == 0.0


def test_calibration_error_positive_when_overconfident() -> None:
    now = datetime.now(UTC)
    # confidence_calibration_error=0.3 with accuracy=0.6 => implied confidence ~0.9.
    results = [
        CaseResult(
            case_id="c1",
            factual_accuracy=0.6,
            critical_omissions=0,
            hallucinations=0,
            confidence_calibration_error=0.3,
            field_comparisons=[],
            hallucination_descriptions=[],
            timestamp=now,
        )
    ]
    err = compute_calibration_error(results)
    assert err > 0.0


def test_field_comparison_schema_roundtrip() -> None:
    fc = FieldComparison(
        field_name="patient_age",
        expected_value=32,
        actual_value=32,
        match=True,
        match_type="exact",
        confidence=1.0,
        weight=2.0,
    )
    # Pydantic must serialize and re-load without loss.
    serialized = fc.model_dump_json()
    fc2 = FieldComparison.model_validate_json(serialized)
    assert fc2 == fc
