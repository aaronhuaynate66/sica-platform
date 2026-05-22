"""Hallucination detection metric.

Two complementary signals:

  1. Field-level hallucinations: a field appears in `actual` with no
     correspondence in `expected` (match_type == 'hallucinated').
  2. Evidence-span hallucinations: a span whose `source_text` is not
     present in the source PDF text. These are detected by the span
     comparator and flagged with match_type == 'hallucinated'.

STRATEGY § 10.3 + § 10.5: hallucination rate is the most safety-critical
quality signal for clinical use. Target in production: <2% of outputs
contain at least one unsupported claim.
"""

from __future__ import annotations

from collections.abc import Iterable

from sica_evals.schemas import FieldComparison


def detect_hallucinations(comparisons: Iterable[FieldComparison]) -> list[str]:
    """Return human-readable descriptions of every hallucination found."""
    descriptions: list[str] = []
    for c in comparisons:
        if c.match_type != "hallucinated":
            continue
        if c.field_name.startswith("evidence_spans"):
            span = c.actual_value or {}
            descriptions.append(
                f"{c.field_name}: span claim={span.get('claim', '?')!r} "
                f"source_text={span.get('source_text', '?')!r} not supported by PDF"
            )
        else:
            descriptions.append(
                f"{c.field_name}: extractor produced {c.actual_value!r}, "
                f"expected absent or null"
            )
    return descriptions


def count_hallucinations(comparisons: Iterable[FieldComparison]) -> int:
    """Total count of hallucination records."""
    return sum(1 for c in comparisons if c.match_type == "hallucinated")
