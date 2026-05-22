"""Critical omissions metric.

A critical omission is a clinically important field that appears in the
expected output (non-empty) but is missing or null in the actual output.

Formal specification:
    docs/evaluation/metrics-specification.md § 2 (Critical Omissions).

Targets (also referenced in ADR 0004 § Nivel 2):
    R0 gate (STRATEGY § 7): critical_omissions_total ≤ 5 per run.
    R1:                      ≤ 2 per run.
    R2 shadow:              ≤ 1 on critical-tagged cases.

Methodology backing this metric (which fields are critical, and why):
    ADR 0005 § "Criticidad del campo se define por proceso".

Special-case handling (per spec):
    - Empty list in actual when expected has elements: each missing element
      counts as one omission (field_comparator decomposes the list).
    - Abnormal labs missing in their entirety: counted as 1 omission (single
      aggregate FieldComparison with weight=2.0).
    - Lab present but `abnormal` flag flipped: mismatch (not omission).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sica_evals.comparators.field_comparator import compare_obstetric_summary
from sica_evals.schemas import FieldComparison


def count_critical_omissions(comparisons: Iterable[FieldComparison]) -> int:
    """Count (weight >= 2.0) AND (match_type == 'missing') comparisons."""
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


def count_critical_omissions_against(
    expected: dict[str, Any],
    actual: dict[str, Any],
    critical_fields: set[str] | None = None,
) -> int:
    """Convenience wrapper matching the (expected, actual, critical_field_list) signature.

    Defaults to the canonical CRITICAL_FIELDS set defined in field_comparator.
    Pass `critical_fields` to override (e.g. for specialty-specific subsets).

    The override path filters by `field_name.startswith(base)` for each base in
    critical_fields, where `base` is the top-level field name without index suffix.
    """
    comparisons = compare_obstetric_summary(expected, actual)

    if critical_fields is None:
        return count_critical_omissions(comparisons)

    def _base(name: str) -> str:
        return name.split("[")[0].split(".")[0]

    return sum(
        1 for c in comparisons
        if c.match_type == "missing" and _base(c.field_name) in critical_fields
    )
