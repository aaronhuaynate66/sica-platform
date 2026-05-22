"""Factual accuracy metric.

Computes weighted fraction of matching field comparisons. Critical fields
(see field_comparator.CRITICAL_FIELDS) are weighted 2x relative to defaults.

Formal specification:
    docs/evaluation/metrics-specification.md § 1 (Factual Accuracy ponderada).

Targets (also referenced in ADR 0004 § Nivel 2):
    R0 gate (STRATEGY § 7):  factual_accuracy_mean ≥ 0.85
    R1:                       ≥ 0.90
    R3+ critical-only:        ≥ 0.95

Methodology decisions backing this metric live in ADR 0005:
    - Paraphrase verbatim-casi handled via FUZZY_RATIO_THRESHOLD (provisional 0.6).
    - Criticality assignment (weight = 2.0) follows field_comparator.CRITICAL_FIELDS
      with documented justification.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sica_evals.comparators.field_comparator import compare_obstetric_summary
from sica_evals.schemas import FieldComparison


def compute_factual_accuracy(comparisons: Iterable[FieldComparison]) -> float:
    """Weighted match ratio across comparisons.

    Returns Σ w(c)·match(c) / Σ w(c) rounded to 4 decimals.
    Convention: empty input returns 0.0 (no measurement possible).
    """
    weighted_match = 0.0
    weighted_total = 0.0
    for c in comparisons:
        weighted_total += c.weight
        if c.match:
            weighted_match += c.weight
    if weighted_total <= 0:
        return 0.0
    return round(weighted_match / weighted_total, 4)


def compute_factual_accuracy_critical_only(
    comparisons: Iterable[FieldComparison],
) -> float:
    """Restricted to fields with weight >= 2.0.

    Tracks the stricter R3+ target (≥0.95 critical-only, STRATEGY § 12.3).
    """
    critical = [c for c in comparisons if c.weight >= 2.0]
    if not critical:
        return 0.0
    matched = sum(1 for c in critical if c.match)
    return round(matched / len(critical), 4)


def compute_factual_accuracy_from_summary(
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> float:
    """Convenience wrapper: take two ObstetricSummary dicts, return factual_accuracy.

    Equivalent to compute_factual_accuracy(compare_obstetric_summary(expected, actual)).
    Matches the (expected, actual) signature requested in issue #11 without breaking
    the canonical (comparisons,) signature used by the harness.
    """
    return compute_factual_accuracy(compare_obstetric_summary(expected, actual))
