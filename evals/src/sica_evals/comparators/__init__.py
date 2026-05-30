"""Field-level, span-level, gate-level y prompt-version comparators."""

from sica_evals.comparators.field_comparator import compare_obstetric_summary
from sica_evals.comparators.gate_comparator import (
    GateResult,
    Violation,
    evaluate_gate,
    load_thresholds,
)
from sica_evals.comparators.prompt_comparator import (
    ComparisonResult,
    compare_prompts_fresh,
    compare_prompts_from_cached,
    compute_verdict,
)
from sica_evals.comparators.prompt_metrics import (
    ComparisonMetrics,
    compare_outputs,
    compute_jaccard,
    extract_keywords,
)
from sica_evals.comparators.span_comparator import compare_evidence_spans, span_in_text

__all__ = [
    "ComparisonMetrics",
    "ComparisonResult",
    "GateResult",
    "Violation",
    "compare_evidence_spans",
    "compare_obstetric_summary",
    "compare_outputs",
    "compare_prompts_fresh",
    "compare_prompts_from_cached",
    "compute_jaccard",
    "compute_verdict",
    "evaluate_gate",
    "extract_keywords",
    "load_thresholds",
    "span_in_text",
]
