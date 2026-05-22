"""Quality metrics for clinical extraction.

Each metric is a pure function. The canonical inputs are FieldComparison
records produced by `comparators.compare_obstetric_summary`, except for
calibration which takes CaseResult lists. Convenience wrappers accept
ObstetricSummary dict pairs directly. Metrics never mutate inputs.

Formal definitions: docs/evaluation/metrics-specification.md
Methodology decisions: docs/decisions/0005-evaluation-methodology.md
"""

from sica_evals.metrics.calibration import (
    compute_calibration_error,
    compute_case_calibration_error,
)
from sica_evals.metrics.critical_omissions import (
    count_critical_omissions,
    count_critical_omissions_against,
    list_critical_omissions,
)
from sica_evals.metrics.factual_accuracy import (
    compute_factual_accuracy,
    compute_factual_accuracy_critical_only,
    compute_factual_accuracy_from_summary,
)
from sica_evals.metrics.hallucinations import (
    count_hallucinations,
    count_hallucinations_by_kind,
    detect_hallucinations,
)

__all__ = [
    "compute_calibration_error",
    "compute_case_calibration_error",
    "compute_factual_accuracy",
    "compute_factual_accuracy_critical_only",
    "compute_factual_accuracy_from_summary",
    "count_critical_omissions",
    "count_critical_omissions_against",
    "count_hallucinations",
    "count_hallucinations_by_kind",
    "detect_hallucinations",
    "list_critical_omissions",
]
