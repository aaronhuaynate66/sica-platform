"""Factual accuracy metric.

Computes weighted fraction of matching field comparisons. Critical fields
(see field_comparator.CRITICAL_FIELDS) are weighted 2x relative to defaults.

STRATEGY § 10.1 + § 12.3 target: ≥0.95 for critical fields in obstetric
summary. R0 gate (STRATEGY § 7): ≥0.85 overall factual accuracy.
"""

from __future__ import annotations

from collections.abc import Iterable

from sica_evals.schemas import FieldComparison


def compute_factual_accuracy(comparisons: Iterable[FieldComparison]) -> float:
    """Weighted match ratio across comparisons. Returns 0.0 if no comparisons."""
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
    """Same as compute_factual_accuracy but restricted to fields with weight >= 2.0.

    Useful for tracking the harder STRATEGY § 12.3 target (≥0.95 critical).
    """
    critical = [c for c in comparisons if c.weight >= 2.0]
    if not critical:
        return 0.0
    matched = sum(1 for c in critical if c.match)
    return round(matched / len(critical), 4)
