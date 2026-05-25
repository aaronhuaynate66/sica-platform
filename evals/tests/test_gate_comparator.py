"""Tests del comparador de gate (evals/src/sica_evals/comparators/gate_comparator.py).

Cubren:
- Threshold passes cuando todas las métricas están dentro.
- Threshold falla cuando factual_accuracy cae más del decline_pp permitido.
- Threshold falla cuando hay >0 hallucinations (absolute_max=0).
- Threshold falla cuando critical_omissions excede absolute_max.
- Threshold falla cuando ECE excede absolute_max.
- Threshold type desconocido genera violation explicativa.
- Métrica ausente en el report genera violation (no crash).
- Baseline ausente desactiva sólo `relative_decline`, no los absolutos.
- ``load_thresholds`` rechaza YAML sin clave ``thresholds``.
"""

from __future__ import annotations

import textwrap
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from sica_evals.comparators.gate_comparator import (
    evaluate_gate,
    load_thresholds,
)
from sica_evals.schemas import HarnessReport


def _make_report(
    *,
    factual: float = 0.92,
    omissions: float = 1.0,
    hallucinations: float = 0.0,
    ece: float = 0.05,
    latency: float = 14.0,
) -> HarnessReport:
    return HarnessReport(
        run_id=str(uuid.uuid4()),
        timestamp=datetime.now(UTC),
        cases_total=1,
        cases_succeeded=1,
        cases_failed=0,
        aggregate_metrics={
            "factual_accuracy_mean": factual,
            "critical_omissions_total": omissions,
            "hallucinations_total": hallucinations,
            "calibration_error_mean": ece,
            "latency_seconds_mean": latency,
        },
        per_case_results=[],
        metadata={},
    )


# El config canónico que usamos en .github/harness-thresholds.yaml.
THRESHOLDS_CANONICAL = {
    "thresholds": {
        "factual_accuracy": {"type": "relative_decline", "max_decline_pp": 3.0},
        "critical_omissions": {"type": "absolute_max", "max_value": 5},
        "hallucination_count": {"type": "absolute_max", "max_value": 0},
        "ece": {"type": "absolute_max", "max_value": 0.15},
    }
}


def test_gate_passes_when_all_metrics_within_threshold() -> None:
    baseline = _make_report(factual=0.92, omissions=1, hallucinations=0, ece=0.05)
    actual = _make_report(factual=0.91, omissions=1, hallucinations=0, ece=0.06)
    result = evaluate_gate(actual, baseline, THRESHOLDS_CANONICAL)
    assert result.passed is True
    assert result.violations == []
    assert "PASSED" in result.summary


def test_gate_fails_when_factual_accuracy_drops_more_than_threshold() -> None:
    baseline = _make_report(factual=0.92)
    # caída de 0.05 absoluto (5pp) — supera el 3.0 permitido
    actual = _make_report(factual=0.87)
    result = evaluate_gate(actual, baseline, THRESHOLDS_CANONICAL)
    assert result.passed is False
    violation_metrics = [v.metric for v in result.violations]
    assert "factual_accuracy" in violation_metrics
    v = next(v for v in result.violations if v.metric == "factual_accuracy")
    assert v.threshold_type == "relative_decline"
    assert "cayó" in v.message


def test_gate_fails_when_hallucinations_present() -> None:
    baseline = _make_report(hallucinations=0)
    actual = _make_report(hallucinations=1)
    result = evaluate_gate(actual, baseline, THRESHOLDS_CANONICAL)
    assert result.passed is False
    assert any(v.metric == "hallucination_count" for v in result.violations)


def test_gate_fails_when_critical_omissions_exceeds_absolute_max() -> None:
    baseline = _make_report(omissions=1)
    actual = _make_report(omissions=7)  # excede el 5 permitido
    result = evaluate_gate(actual, baseline, THRESHOLDS_CANONICAL)
    assert result.passed is False
    assert any(v.metric == "critical_omissions" for v in result.violations)


def test_gate_fails_when_ece_exceeds_absolute_max() -> None:
    baseline = _make_report(ece=0.03)
    actual = _make_report(ece=0.20)
    result = evaluate_gate(actual, baseline, THRESHOLDS_CANONICAL)
    assert result.passed is False
    assert any(v.metric == "ece" for v in result.violations)


def test_gate_unknown_threshold_type_emits_violation() -> None:
    cfg = {
        "thresholds": {
            "factual_accuracy": {"type": "weird_unsupported_type", "max_value": 1},
        }
    }
    actual = _make_report()
    baseline = _make_report()
    result = evaluate_gate(actual, baseline, cfg)
    assert result.passed is False
    assert any("no soportado" in v.message for v in result.violations)


def test_gate_missing_metric_emits_violation() -> None:
    cfg = {
        "thresholds": {
            "totally_made_up_metric": {"type": "absolute_max", "max_value": 0},
        }
    }
    actual = _make_report()
    result = evaluate_gate(actual, None, cfg)
    assert result.passed is False
    assert any("no presente" in v.message for v in result.violations), result.violations


def test_gate_without_baseline_skips_relative_decline_but_evaluates_absolutes() -> None:
    cfg = {
        "thresholds": {
            "factual_accuracy": {"type": "relative_decline", "max_decline_pp": 3.0},
            "hallucination_count": {"type": "absolute_max", "max_value": 0},
        }
    }
    # sin baseline: relative_decline se omite; hallucination_count sí evalúa
    bad = _make_report(hallucinations=2)
    result = evaluate_gate(bad, None, cfg)
    assert result.passed is False
    assert any(v.metric == "hallucination_count" for v in result.violations)
    assert not any(v.metric == "factual_accuracy" for v in result.violations)

    good = _make_report(hallucinations=0)
    result_ok = evaluate_gate(good, None, cfg)
    assert result_ok.passed is True


def test_load_thresholds_reads_yaml_and_returns_dict(tmp_path: Path) -> None:
    yaml_text = textwrap.dedent(
        """
        thresholds:
          factual_accuracy:
            type: "relative_decline"
            max_decline_pp: 3.0
        config:
          baseline_path: "fixtures/baselines/x.json"
        """
    ).strip()
    path = tmp_path / "th.yaml"
    path.write_text(yaml_text, encoding="utf-8")
    cfg = load_thresholds(path)
    assert "thresholds" in cfg
    assert cfg["thresholds"]["factual_accuracy"]["max_decline_pp"] == 3.0


def test_load_thresholds_rejects_yaml_without_thresholds_key(tmp_path: Path) -> None:
    path = tmp_path / "broken.yaml"
    path.write_text("config:\n  foo: bar\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no tiene clave 'thresholds'"):
        load_thresholds(path)


def test_load_thresholds_missing_file_raises(tmp_path: Path) -> None:
    missing = tmp_path / "nope.yaml"
    with pytest.raises(FileNotFoundError):
        load_thresholds(missing)
