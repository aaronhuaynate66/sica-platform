"""Hallucination detection metric.

Two complementary signals (per spec):

  1. H_field — field-level hallucinations: a field appears in `actual` with
     no correspondence in `expected` (match_type == 'hallucinated' and
     field_name does NOT start with 'evidence_spans').
  2. H_span — evidence-span hallucinations: a span whose `source_text` is
     not present in the source PDF text. Detected by span_comparator and
     marked with match_type == 'hallucinated' under field_name starting
     with 'evidence_spans'.

  hallucinations = |H_field| + |H_span|

Formal specification:
    docs/evaluation/metrics-specification.md § 3 (Hallucinations).

Target (STRATEGY § 11.1 principle 4: "abstention over hallucination"):
    R0 gate:  hallucinations = 0. Zero tolerance.
    R1+:       hallucinations = 0.

A single clinically-credible hallucination kills physician trust.
This metric is NOT averaged or weighted — it is summed and gated at 0.
"""

from __future__ import annotations

from collections.abc import Iterable

from sica_evals.schemas import FieldComparison


def _is_span_field(field_name: str) -> bool:
    """True if the FieldComparison corresponds to an evidence_spans entry."""
    return field_name.startswith("evidence_spans")


def detect_hallucinations(comparisons: Iterable[FieldComparison]) -> list[str]:
    """Human-readable description of every hallucination found.

    Separates H_field and H_span in the rendered message for downstream
    reporters / triage. The returned list is the canonical input to the
    Markdown / HTML reporters' "critical findings" section.
    """
    descriptions: list[str] = []
    for c in comparisons:
        if c.match_type != "hallucinated":
            continue
        if _is_span_field(c.field_name):
            # H_span: span fabricated or not present in PDF text.
            span = c.actual_value or {}
            descriptions.append(
                f"[H_span] {c.field_name}: claim={span.get('claim', '?')!r} "
                f"source_text={span.get('source_text', '?')!r} not supported by PDF"
            )
        else:
            # H_field: extractor produced a value where expected had None/absent.
            descriptions.append(
                f"[H_field] {c.field_name}: extractor produced {c.actual_value!r}, "
                f"expected absent or null"
            )
    return descriptions


def count_hallucinations(comparisons: Iterable[FieldComparison]) -> int:
    """Total count of hallucination records (H_field + H_span)."""
    return sum(1 for c in comparisons if c.match_type == "hallucinated")


def count_hallucinations_by_kind(
    comparisons: Iterable[FieldComparison],
) -> tuple[int, int]:
    """Return (|H_field|, |H_span|) separately. Useful for triage and reporting."""
    comps = list(comparisons)
    h_span = sum(
        1 for c in comps
        if c.match_type == "hallucinated" and _is_span_field(c.field_name)
    )
    h_field = sum(
        1 for c in comps
        if c.match_type == "hallucinated" and not _is_span_field(c.field_name)
    )
    return h_field, h_span
