"""Critical omissions metric.

A critical omission is a clinically important field that appears in the
expected output (non-empty) but is missing or null in the actual output.

STRATEGY § 10.2 + § 7: R0 gate ≤5% critical omissions across cases.
"""

from __future__ import annotations

from collections.abc import Iterable

from sica_evals.schemas import FieldComparison


def count_critical_omissions(comparisons: Iterable[FieldComparison]) -> int:
    """Count comparisons that are (weight >= 2.0) AND match_type == 'missing'.

    Also counts lab_results with abnormal=True that ended up missing — the
    field comparator already marks these with weight=2.0.
    """
    return sum(
        1 for c in comparisons
        if c.weight >= 2.0 and c.match_type == "missing"
    )


def list_critical_omissions(
    comparisons: Iterable[FieldComparison],
) -> list[FieldComparison]:
    """Return the FieldComparison records flagged as critical omissions."""
    return [
        c for c in comparisons
        if c.weight >= 2.0 and c.match_type == "missing"
    ]
