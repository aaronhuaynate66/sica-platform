"""Tests del comparator offline de prompts.

Cubre:
    - Primitivas (Jaccard, extract_keywords).
    - compare_outputs en escenarios típicos: idénticos, regresiones,
      mejoras, removed/added en active_problems.
    - compute_verdict: GREEN/YELLOW/RED con thresholds.
    - End-to-end sobre el dataset Lucía (4 PDFs) en modo cached.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sica_evals.comparators.prompt_comparator import (
    compare_prompts_from_cached,
    compute_verdict,
)
from sica_evals.comparators.prompt_metrics import (
    compare_outputs,
    compute_jaccard,
    extract_keywords,
)

# ---------------------------------------------------------------------------
# compute_jaccard
# ---------------------------------------------------------------------------

def test_compute_jaccard_identical_sets_returns_one() -> None:
    assert compute_jaccard({"a", "b", "c"}, {"a", "b", "c"}) == 1.0


def test_compute_jaccard_disjoint_sets_returns_zero() -> None:
    assert compute_jaccard({"a", "b"}, {"x", "y"}) == 0.0


def test_compute_jaccard_case_insensitive_and_trims() -> None:
    assert compute_jaccard({"Diabetes "}, {" diabetes"}) == 1.0


def test_compute_jaccard_empty_sets_returns_one() -> None:
    assert compute_jaccard(set(), set()) == 1.0


def test_compute_jaccard_partial_overlap() -> None:
    # intersección = {b}, unión = {a,b,c} → 1/3
    assert compute_jaccard({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)


# ---------------------------------------------------------------------------
# extract_keywords
# ---------------------------------------------------------------------------

def test_extract_keywords_removes_stopwords() -> None:
    kws = extract_keywords("La paciente con embarazo y diabetes para control")
    # de, la, con, y, para son stopwords
    assert "la" not in kws
    assert "con" not in kws
    assert "para" not in kws
    # Contenido real debe estar
    assert "paciente" in kws
    assert "embarazo" in kws
    assert "diabetes" in kws


def test_extract_keywords_empty_text_returns_empty_set() -> None:
    assert extract_keywords("") == set()


def test_extract_keywords_respects_top_n() -> None:
    # 10 palabras únicas, top_n=3 → 3 keywords como máximo.
    text = "alfa beto gama delta epsilon zeta eta theta iota kappa"
    kws = extract_keywords(text, top_n=3)
    assert len(kws) <= 3


# ---------------------------------------------------------------------------
# compare_outputs — escenarios sintéticos
# ---------------------------------------------------------------------------

def _base_summary() -> dict:
    """Output mínimo válido como baseline para tests sintéticos."""
    return {
        "patient_age": 28,
        "gestational_age_weeks": 16.3,
        "fum": "2023-12-27",
        "fpp": "2024-10-03",
        "active_problems": ["Sobrepeso pre-gestacional", "Embarazo de 16 semanas"],
        "risk_factors": ["Antecedente familiar DM2"],
        "lab_results": [{"name": "Hb", "value": "11.8", "unit": "g/dL"}],
        "notes_summary": "Control prenatal sin complicaciones agudas.",
        "confidence_score": 0.95,
        "evidence_spans": [{"claim": "Edad", "source_page": 1, "source_text": "28 años"}],
    }


def test_compare_outputs_identical_inputs_no_regressions() -> None:
    summary = _base_summary()
    m = compare_outputs("case_x", summary, summary)
    assert m.regressions == []
    assert m.patient_age_match is True
    assert m.gestational_age_match is True
    assert m.fum_match is True
    assert m.fpp_match is True
    assert m.active_problems_overlap == 1.0
    assert m.active_problems_added == []
    assert m.active_problems_removed == []


def test_compare_outputs_detects_pregnancy_removed_from_active_problems() -> None:
    v1 = _base_summary()
    v2 = _base_summary()
    v2["active_problems"] = ["Sobrepeso pre-gestacional"]  # quitó "Embarazo de 16 semanas"
    m = compare_outputs("lucia_sem16", v1, v2)
    assert m.active_problems_removed == ["Embarazo de 16 semanas"]
    assert m.active_problems_added == []
    assert "active_problems_conciseness" in m.improvements
    assert m.regressions == []


def test_compare_outputs_detects_regression_in_gestational_age() -> None:
    v1 = _base_summary()
    v2 = _base_summary()
    v2["gestational_age_weeks"] = 22.0  # delta 5.7 >> 0.5
    m = compare_outputs("case_x", v1, v2)
    assert m.gestational_age_match is False
    assert "gestational_age_weeks" in m.regressions


def test_compare_outputs_detects_confidence_drop() -> None:
    v1 = _base_summary()
    v2 = _base_summary()
    v2["confidence_score"] = 0.70  # -0.25 vs 0.95
    m = compare_outputs("case_x", v1, v2)
    assert "confidence_score" in m.regressions
    assert m.confidence_delta == pytest.approx(-0.25)


def test_compare_outputs_detects_confidence_improvement() -> None:
    v1 = _base_summary()
    v1["confidence_score"] = 0.70
    v2 = _base_summary()
    v2["confidence_score"] = 0.95
    m = compare_outputs("case_x", v1, v2)
    assert "confidence_score" in m.improvements


def test_compare_outputs_detects_lab_results_loss() -> None:
    v1 = _base_summary()
    v1["lab_results"] = [{"name": f"lab{i}", "value": "x"} for i in range(10)]
    v2 = _base_summary()
    v2["lab_results"] = [{"name": "lab0", "value": "x"}]  # perdió 90%
    m = compare_outputs("case_x", v1, v2)
    assert "lab_results_count" in m.regressions


def test_compare_outputs_handles_missing_metadata_gracefully() -> None:
    v1 = _base_summary()
    v2 = _base_summary()
    m = compare_outputs("case_x", v1, v2, metadata_v1=None, metadata_v2=None)
    assert m.cost_v1_usd is None
    assert m.cost_v2_usd is None
    assert m.cost_delta_usd is None
    assert m.latency_delta_ms is None


def test_compare_outputs_uses_metadata_when_provided() -> None:
    v1 = _base_summary()
    v2 = _base_summary()
    m = compare_outputs(
        "case_x",
        v1,
        v2,
        metadata_v1={"cost_usd": 0.04, "latency_ms": 3000},
        metadata_v2={"cost_usd": 0.05, "latency_ms": 3800},
    )
    assert m.cost_v1_usd == 0.04
    assert m.cost_v2_usd == 0.05
    assert m.cost_delta_usd == pytest.approx(0.01)
    assert m.latency_delta_ms == 800
    assert "cost_usd" in m.neutral_changes
    assert "latency_ms" in m.neutral_changes


# ---------------------------------------------------------------------------
# compute_verdict
# ---------------------------------------------------------------------------

def _metrics_with(
    regressions: list[str] | None = None,
    improvements: list[str] | None = None,
) -> object:
    """Builder ligero de ``ComparisonMetrics`` para tests de verdict."""
    summary = _base_summary()
    m = compare_outputs("case_x", summary, summary)
    # ComparisonMetrics es frozen; reemplazamos con dataclasses.replace
    from dataclasses import replace
    return replace(
        m,
        regressions=regressions or [],
        improvements=improvements or [],
    )


def test_compute_verdict_zero_cases_returns_red() -> None:
    verdict, reason = compute_verdict([])
    assert verdict == "RED"
    assert "Sin casos" in reason


def test_compute_verdict_green_when_majority_improvements_zero_regressions() -> None:
    cases = [
        _metrics_with(improvements=["x"]),
        _metrics_with(improvements=["x"]),
        _metrics_with(improvements=["x"]),
        _metrics_with(),  # neutral
    ]
    verdict, _ = compute_verdict(cases)
    assert verdict == "GREEN"


def test_compute_verdict_red_when_25pct_regressions() -> None:
    cases = [
        _metrics_with(regressions=["confidence_score"]),
        _metrics_with(regressions=["confidence_score"]),
        _metrics_with(),
        _metrics_with(),
    ]
    verdict, _ = compute_verdict(cases)
    assert verdict == "RED"


def test_compute_verdict_yellow_when_borderline_regressions() -> None:
    cases = [
        _metrics_with(regressions=["confidence_score"]),  # 1/10 = 10%
        *[_metrics_with() for _ in range(9)],
    ]
    verdict, _ = compute_verdict(cases)
    assert verdict == "YELLOW"


def test_compute_verdict_critical_field_regression_forces_red() -> None:
    # Solo un caso, pero perdió fum → hard-fail aun siendo el único caso.
    cases = [_metrics_with(regressions=["fum"])]
    verdict, reason = compute_verdict(cases)
    assert verdict == "RED"
    assert "fum" in reason


# ---------------------------------------------------------------------------
# compare_prompts_from_cached — E2E sobre dataset Lucía
# ---------------------------------------------------------------------------

LUCIA_FIXTURES = (
    Path(__file__).resolve().parents[1] / "fixtures" / "longitudinal_lucia"
)


@pytest.mark.skipif(
    not LUCIA_FIXTURES.exists(), reason="Dataset Lucía no presente en el repo"
)
def test_compare_from_cached_with_lucia_dataset() -> None:
    result = compare_prompts_from_cached(
        prompt_name="extract_obstetric",
        version_a=1,
        version_b=2,
        fixtures_dir=LUCIA_FIXTURES,
    )
    # El dataset tiene 4 controles (sem16, sem24, sem32, sem38). Cada uno
    # tiene extracted.json + extracted_v2.json.
    assert result.n_cases == 4
    assert result.prompt_name == "extract_obstetric"
    assert result.version_a == 1
    assert result.version_b == 2
    # Cada caso debe preservar identidad temporal (patient_age, FUM, FPP, GA).
    for m in result.case_metrics:
        assert m.patient_age_match, f"{m.case_id}: patient_age regresionó"
        assert m.fum_match, f"{m.case_id}: FUM regresionó"
        assert m.fpp_match, f"{m.case_id}: FPP regresionó"


def test_compare_from_cached_skips_cases_without_both_fixtures(tmp_path: Path) -> None:
    # Caso A: tiene ambos archivos → debe contar.
    case_a = tmp_path / "case_a"
    case_a.mkdir()
    (case_a / "extracted.json").write_text(json.dumps(_base_summary()), encoding="utf-8")
    (case_a / "extracted_v2.json").write_text(json.dumps(_base_summary()), encoding="utf-8")
    # Caso B: solo tiene v1 → debe saltarse.
    case_b = tmp_path / "case_b"
    case_b.mkdir()
    (case_b / "extracted.json").write_text(json.dumps(_base_summary()), encoding="utf-8")

    result = compare_prompts_from_cached(
        prompt_name="extract_obstetric",
        version_a=1,
        version_b=2,
        fixtures_dir=tmp_path,
    )
    assert result.n_cases == 1
    assert result.case_metrics[0].case_id == "case_a"


def test_compare_from_cached_raises_on_missing_dir(tmp_path: Path) -> None:
    missing = tmp_path / "no_existe"
    with pytest.raises(FileNotFoundError):
        compare_prompts_from_cached(
            prompt_name="extract_obstetric",
            version_a=1,
            version_b=2,
            fixtures_dir=missing,
        )
