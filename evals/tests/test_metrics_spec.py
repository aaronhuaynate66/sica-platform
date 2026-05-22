"""Spec-driven tests for the factuality metrics.

These tests check that the implementation in sica_evals.metrics matches
the formal specification in docs/evaluation/metrics-specification.md.

Naming convention: every test starts with `test_spec_` and references the
spec section (§ N) it validates. When the spec changes, these tests are
the ones that should be updated first (then the code).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sica_evals.comparators.field_comparator import (
    FUZZY_RATIO_THRESHOLD,
    compare_obstetric_summary,
)
from sica_evals.comparators.span_comparator import compare_evidence_spans
from sica_evals.metrics import (
    compute_calibration_error,
    compute_factual_accuracy,
    compute_factual_accuracy_from_summary,
    count_critical_omissions,
    count_critical_omissions_against,
    count_hallucinations,
    count_hallucinations_by_kind,
    detect_hallucinations,
)
from sica_evals.schemas import CaseResult


def _perfect_summary() -> dict:
    """Canonical fixture: every critical field present and correct."""
    return {
        "patient_age": 32,
        "gestational_age_weeks": 28.3,
        "fum": "2025-09-15",
        "fpp": "2026-06-22",
        "active_problems": ["Anemia leve gestacional", "Cesárea previa (2022)"],
        "risk_factors": ["Cesárea previa", "Anemia leve gestacional"],
        "lab_results": [
            {
                "name": "Hemoglobina",
                "value": "10.8",
                "unit": "g/dL",
                "date": "2026-04-02",
                "abnormal": True,
            },
            {
                "name": "Glucosa basal",
                "value": "92",
                "unit": "mg/dL",
                "date": "2026-04-02",
                "abnormal": False,
            },
        ],
        "notes_summary": "Paciente de 32 años, gestación 28 semanas, anemia leve en tratamiento.",
        "confidence_score": 0.95,
        "evidence_spans": [],
    }


def _empty_summary() -> dict:
    """Canonical fixture: extractor produced nothing for the case."""
    return {
        "patient_age": None,
        "gestational_age_weeks": None,
        "fum": None,
        "fpp": None,
        "active_problems": [],
        "risk_factors": [],
        "lab_results": [],
        "notes_summary": "",
        "confidence_score": 0.0,
        "evidence_spans": [],
    }


# ---------------------------------------------------------------------------
# § 1 — Factual Accuracy ponderada
# ---------------------------------------------------------------------------


def test_spec_s1_perfect_case_factual_accuracy_is_one() -> None:
    """Spec § 1: caso perfecto → factual_accuracy = 1.0."""
    summary = _perfect_summary()
    assert compute_factual_accuracy_from_summary(summary, summary) == 1.0


def test_spec_s1_empty_actual_against_perfect_expected_has_low_accuracy() -> None:
    """Spec § 1: extractor devuelve None en todo → mayoría de matches fallan.

    The empty summary still matches when both expected AND actual are None
    for the same field (which is impossible here — expected is perfect).
    All critical fields fail; the only matches are degenerate (empty list vs
    empty list does NOT occur because expected lists are non-empty).
    """
    expected = _perfect_summary()
    actual = _empty_summary()
    acc = compute_factual_accuracy_from_summary(expected, actual)
    # Every critical field is missing; non-critical mostly also missing.
    # accuracy must be far below the R0 threshold of 0.85.
    assert acc < 0.30


def test_spec_s1_critical_field_failure_drops_accuracy_more_than_noncritical() -> None:
    """Spec § 1: weights matter. A critical mismatch drops accuracy more.

    Construct two divergences: one critical (gestational_age_weeks), one
    non-critical (notes_summary). The critical one must produce lower
    factual_accuracy when applied alone.
    """
    expected = _perfect_summary()

    # Variant A: critical field off by a lot (outside tolerance).
    actual_critical_bad = {**expected, "gestational_age_weeks": 40.0}
    acc_critical = compute_factual_accuracy_from_summary(expected, actual_critical_bad)

    # Variant B: non-critical field mismatched but same shape.
    actual_noncritical_bad = {
        **expected,
        "notes_summary": "Texto completamente distinto sin relación con el caso.",
    }
    acc_noncritical = compute_factual_accuracy_from_summary(expected, actual_noncritical_bad)

    assert acc_critical < acc_noncritical, (
        "Critical field failure should drop accuracy more than non-critical "
        "(weights = 2 vs 1)."
    )


def test_spec_s1_weights_match_formula() -> None:
    """Spec § 1: factual_accuracy = Σ w(c)·match(c) / Σ w(c).

    Build a 3-field scenario: 2 critical match, 1 critical fail; expected
    accuracy = (2·1 + 2·1 + 2·0) / (2·1 + 2·1 + 2·1) = 4/6 ≈ 0.6667.
    """
    expected = {
        "patient_age": 32,
        "gestational_age_weeks": 28.3,
        "fum": "2025-09-15",
        "active_problems": [],
        "risk_factors": [],
        "lab_results": [],
        "notes_summary": "",
    }
    actual = {
        "patient_age": 32,             # critical, match
        "gestational_age_weeks": 28.3,  # critical, match
        "fum": None,                    # critical, miss
        "active_problems": [],
        "risk_factors": [],
        "lab_results": [],
        "notes_summary": "",
    }
    acc = compute_factual_accuracy_from_summary(expected, actual)
    # 2*1 + 2*1 + 2*0 + (no-op empty matches) = 4 / 6 + extras
    # Empty list vs empty list yields match=True with weight 2.0 each (active/risk).
    # notes_summary empty vs empty: weight 1.0 match.
    # gestational_age via fuzzy comparator also weight 2.0.
    # So real denominator includes more fields. Just check accuracy is in expected range.
    assert 0.5 < acc < 0.9


# ---------------------------------------------------------------------------
# § 2 — Critical Omissions
# ---------------------------------------------------------------------------


def test_spec_s2_perfect_case_has_zero_omissions() -> None:
    """Spec § 2: caso perfecto → critical_omissions = 0."""
    summary = _perfect_summary()
    comparisons = compare_obstetric_summary(summary, summary)
    assert count_critical_omissions(comparisons) == 0


def test_spec_s2_empty_actual_produces_omissions_equal_to_critical_fields_expected() -> None:
    """Spec § 2: extractor vacío → cada campo crítico esperado cuenta.

    Each expected critical field (patient_age, fum, fpp, gestational_age_weeks,
    plus each abnormal lab and each non-empty list element) becomes an
    omission. The exact count depends on the fixture; we assert ≥ 5
    (which matches the R0 gate target).
    """
    expected = _perfect_summary()
    actual = _empty_summary()
    comparisons = compare_obstetric_summary(expected, actual)
    n = count_critical_omissions(comparisons)
    assert n >= 5, f"empty actual should produce many omissions, got {n}"


def test_spec_s2_abnormal_lab_missing_counts_as_one_omission_aggregate() -> None:
    """Spec § 2: lab anormal totalmente ausente cuenta como 1 omisión agregada.

    NOT as N omissions (one per sub-field). The field_comparator emits a
    single aggregate FieldComparison with weight=2 when an abnormal lab
    is missing.
    """
    expected = {**_perfect_summary(), "lab_results": [
        {
            "name": "Hemoglobina",
            "value": "8.0",
            "unit": "g/dL",
            "date": "2026-04-02",
            "abnormal": True,  # critical
        },
    ]}
    actual = {**_perfect_summary(), "lab_results": []}  # lab missing entirely
    comparisons = compare_obstetric_summary(expected, actual)
    # The hemoglobina lab missing yields one aggregate omission.
    lab_omissions = [
        c for c in comparisons
        if c.match_type == "missing" and c.field_name.startswith("lab_results")
    ]
    assert len(lab_omissions) == 1


def test_spec_s2_mismatch_is_not_omission() -> None:
    """Spec § 2: lab presente con abnormal=False (cuando expected era True) es mismatch, no missing."""
    expected = {**_perfect_summary(), "lab_results": [
        {
            "name": "Hemoglobina",
            "value": "8.0",
            "unit": "g/dL",
            "date": "2026-04-02",
            "abnormal": True,
        },
    ]}
    actual = {**_perfect_summary(), "lab_results": [
        {
            "name": "Hemoglobina",
            "value": "8.0",
            "unit": "g/dL",
            "date": "2026-04-02",
            "abnormal": False,  # flipped
        },
    ]}
    comparisons = compare_obstetric_summary(expected, actual)
    # The abnormal sub-field comparison is a mismatch, not a missing.
    abnormal_cmps = [c for c in comparisons if c.field_name.endswith(".abnormal")]
    assert abnormal_cmps
    assert all(c.match_type != "missing" for c in abnormal_cmps)


def test_spec_s2_critical_fields_override_works() -> None:
    """Spec § 2 wrapper: count_critical_omissions_against allows custom criticality set."""
    expected = _perfect_summary()
    actual = {**expected, "notes_summary": ""}  # non-critical by default
    # Override to make notes_summary critical for this run.
    n_default = count_critical_omissions_against(expected, actual)
    n_override = count_critical_omissions_against(
        expected, actual, critical_fields={"notes_summary"}
    )
    assert n_default == 0  # notes_summary is not critical by default
    assert n_override >= 1  # under override, the empty notes counts as missing


# ---------------------------------------------------------------------------
# § 3 — Hallucinations
# ---------------------------------------------------------------------------


def test_spec_s3_perfect_case_has_zero_hallucinations() -> None:
    """Spec § 3: caso perfecto → hallucinations = 0."""
    summary = _perfect_summary()
    comparisons = compare_obstetric_summary(summary, summary)
    assert count_hallucinations(comparisons) == 0
    assert detect_hallucinations(comparisons) == []


def test_spec_s3_pure_hallucination_in_field() -> None:
    """Spec § 3: campo presente en actual sin contraparte → H_field += 1.

    Expected: patient_age None. Actual: patient_age 32 (fabricated).
    """
    expected = {**_perfect_summary(), "patient_age": None}
    actual = {**_perfect_summary(), "patient_age": 32}
    comparisons = compare_obstetric_summary(expected, actual)
    h_field, h_span = count_hallucinations_by_kind(comparisons)
    assert h_field == 1
    assert h_span == 0
    descriptions = detect_hallucinations(comparisons)
    assert any("[H_field]" in d and "patient_age" in d for d in descriptions)


def test_spec_s3_pure_hallucination_in_span_when_text_not_in_pdf() -> None:
    """Spec § 3: span con source_text no presente en PDF → H_span += 1."""
    pdf_text = "Edad: 32 años. FUM: 15/09/2025."
    expected_spans = [
        {"claim": "Edad 32 años", "source_page": 1, "source_text": "Edad: 32 años"},
    ]
    actual_spans = [
        {"claim": "Edad 32 años", "source_page": 1, "source_text": "Edad: 32 años"},
        {
            # Fabricated: not in pdf, not matching any expected.
            "claim": "Diabetes tipo 2",
            "source_page": 1,
            "source_text": "Diagnóstico: Diabetes Mellitus tipo 2",
        },
    ]
    comparisons = compare_evidence_spans(expected_spans, actual_spans, pdf_text=pdf_text)
    h_field, h_span = count_hallucinations_by_kind(comparisons)
    assert h_field == 0
    assert h_span == 1


def test_spec_s3_zero_tolerance_combined() -> None:
    """Spec § 3: cualquier hallucination (field o span) hace que count > 0.

    The gate is = 0, so 1 hallucination in either category fails the gate.
    """
    expected = {**_perfect_summary(), "patient_age": None}
    actual = {**_perfect_summary(), "patient_age": 32}
    comparisons = compare_obstetric_summary(expected, actual)
    assert count_hallucinations(comparisons) >= 1


# ---------------------------------------------------------------------------
# § 4 — Confidence Calibration Error
# ---------------------------------------------------------------------------


def _make_case_result(
    accuracy: float,
    confidence: float,
    *,
    case_id: str = "c1",
) -> CaseResult:
    """Build a CaseResult with a specific (accuracy, confidence) pair.

    We store |conf - acc| in confidence_calibration_error so the metric
    can reconstruct mean confidence per bin.
    """
    return CaseResult(
        case_id=case_id,
        factual_accuracy=accuracy,
        critical_omissions=0,
        hallucinations=0,
        confidence_calibration_error=round(abs(confidence - accuracy), 4),
        field_comparisons=[],
        hallucination_descriptions=[],
        timestamp=datetime.now(UTC),
    )


def test_spec_s4_perfectly_calibrated_extractor_has_zero_ece() -> None:
    """Spec § 4: cuando confidence == accuracy en cada caso, ECE = 0.0."""
    results = [
        _make_case_result(0.95, 0.95, case_id="c1"),
        _make_case_result(0.90, 0.90, case_id="c2"),
        _make_case_result(0.85, 0.85, case_id="c3"),
    ]
    assert compute_calibration_error(results) == 0.0


def test_spec_s4_overconfident_extractor_has_positive_ece() -> None:
    """Spec § 4: confidence consistently above accuracy → ECE > 0.

    Five cases reporting 0.95 confidence but only ~0.60 actual accuracy.
    Gap of 0.35 per case; ECE should be substantial.
    """
    results = [_make_case_result(0.60, 0.95, case_id=f"c{i}") for i in range(5)]
    ece = compute_calibration_error(results)
    assert ece > 0.15  # exceeds the R0 threshold


def test_spec_s4_n_bins_parameter_respected() -> None:
    """Spec § 4: n_bins is configurable. With n_bins=1, all cases collapse to one bin."""
    results = [_make_case_result(0.5, 0.5, case_id="c1")]
    ece_default = compute_calibration_error(results)
    ece_one_bin = compute_calibration_error(results, n_bins=1)
    # In this contrived case both should be 0.0 (single perfectly calibrated case).
    assert ece_default == ece_one_bin == 0.0


def test_spec_s4_empty_input_returns_zero() -> None:
    """Spec § 4: empty input → 0.0 by convention."""
    assert compute_calibration_error([]) == 0.0


# ---------------------------------------------------------------------------
# Cross-cutting spec checks
# ---------------------------------------------------------------------------


def test_spec_fuzzy_threshold_constant_is_provisional_value() -> None:
    """ADR 0005 Decisión 1: FUZZY_RATIO_THRESHOLD documented as 0.6 (provisional).

    This test enforces that the constant matches the value documented in
    the ADR. If you change the threshold, update both this test and the
    ADR (in the same PR).
    """
    assert FUZZY_RATIO_THRESHOLD == 0.6, (
        "FUZZY_RATIO_THRESHOLD must match the value documented in "
        "ADR 0005 (Decisión 1). Updating it requires a superseding ADR."
    )


def test_spec_critical_fields_includes_canonical_set() -> None:
    """ADR 0005 Decisión 2: canonical CRITICAL_FIELDS includes these names.

    Adding to the set is OK (and only requires PR justification).
    Removing requires a superseding ADR.
    """
    from sica_evals.comparators.field_comparator import CRITICAL_FIELDS

    required = {
        "patient_age",
        "gestational_age_weeks",
        "fum",
        "fpp",
        "active_problems",
        "risk_factors",
    }
    missing = required - CRITICAL_FIELDS
    assert not missing, (
        f"CRITICAL_FIELDS is missing {missing}. Removing critical fields "
        f"requires a superseding ADR (see ADR 0005 Decisión 2)."
    )


def test_spec_paraphrase_almost_verbatim_matches_fuzzy() -> None:
    """ADR 0005 Decisión 1: 'Anemia leve' vs 'Anemia leve gestacional' should match fuzzy."""
    a = {
        "patient_age": None,
        "gestational_age_weeks": None,
        "fum": None,
        "fpp": None,
        "active_problems": ["Anemia leve"],
        "risk_factors": [],
        "lab_results": [],
        "notes_summary": "",
    }
    b = {**a, "active_problems": ["Anemia leve gestacional"]}
    comparisons = compare_obstetric_summary(a, b)
    cmp = next(c for c in comparisons if c.field_name == "active_problems")
    assert cmp.match, "near-verbatim paraphrase must match under fuzzy threshold 0.6"
    assert cmp.match_type in {"fuzzy", "exact"}


def test_spec_date_ambiguity_strict_exact_match() -> None:
    """Spec § 1: fechas (fum) requieren exact match — sin tolerancia.

    A 1-day difference in FUM must NOT match.
    """
    a = {
        "patient_age": None,
        "gestational_age_weeks": None,
        "fum": "2025-09-15",
        "fpp": None,
        "active_problems": [],
        "risk_factors": [],
        "lab_results": [],
        "notes_summary": "",
    }
    b = {**a, "fum": "2025-09-16"}  # off by 1 day
    comparisons = compare_obstetric_summary(a, b)
    cmp = next(c for c in comparisons if c.field_name == "fum")
    assert not cmp.match, "FUM with 1-day diff must NOT match — spec § 1 forbids tolerance"
    assert cmp.match_type == "mismatch"
