"""Field-level, span-level y gate-level comparators."""

from sica_evals.comparators.field_comparator import compare_obstetric_summary
from sica_evals.comparators.gate_comparator import (
    GateResult,
    Violation,
    evaluate_gate,
    load_thresholds,
)
from sica_evals.comparators.span_comparator import compare_evidence_spans, span_in_text

__all__ = [
    "GateResult",
    "Violation",
    "compare_evidence_spans",
    "compare_obstetric_summary",
    "evaluate_gate",
    "load_thresholds",
    "span_in_text",
]
