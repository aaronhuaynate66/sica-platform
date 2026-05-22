"""Quality metrics for clinical extraction.

Each metric is a pure function over CaseResult (or list thereof) returning
a scalar or count. Metrics never mutate inputs.
"""

from sica_evals.metrics.calibration import compute_calibration_error
from sica_evals.metrics.critical_omissions import count_critical_omissions
from sica_evals.metrics.factual_accuracy import compute_factual_accuracy
from sica_evals.metrics.hallucinations import detect_hallucinations

__all__ = [
    "compute_calibration_error",
    "compute_factual_accuracy",
    "count_critical_omissions",
    "detect_hallucinations",
]
