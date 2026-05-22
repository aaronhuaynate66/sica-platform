"""Confidence calibration metric.

Compares the model-reported `confidence_score` against observed factual
accuracy. A well-calibrated extractor reporting 0.9 confidence should
actually be correct ~90% of the time.

Formal specification:
    docs/evaluation/metrics-specification.md § 4 (Confidence Calibration Error).

Targets (also referenced in ADR 0004 § Nivel 2):
    R0:  ECE ≤ 0.15
    R1+: ECE ≤ 0.10

Why this metric matters (STRATEGY § 11.4):
    SICA uses `confidence_score` to gate abstention. A miscalibrated
    extractor that reports 0.95 but is only 60% accurate breaks the
    abstention safety net — the system "feels confident" while being wrong.
"""

from __future__ import annotations

from collections.abc import Iterable

from sica_evals.schemas import CaseResult


DEFAULT_N_BINS = 10


def compute_case_calibration_error(
    reported_confidence: float,
    observed_accuracy: float,
) -> float:
    """Per-case absolute deviation: |confidence - accuracy|. Range [0, 1]."""
    return round(abs(reported_confidence - observed_accuracy), 4)


def compute_calibration_error(
    case_results: Iterable[CaseResult],
    *,
    n_bins: int = DEFAULT_N_BINS,
) -> float:
    """Expected Calibration Error across cases.

    Partition cases into `n_bins` equal-width buckets by their
    `factual_accuracy`, then sum (|B_k| / N) · |conf(B_k) - acc(B_k)|.

    Parameters
    ----------
    case_results:
        Iterable of CaseResult instances from a single run.
    n_bins:
        Number of bins for ECE. Default 10. Must be >= 1.

    Convention: empty input returns 0.0 (no measurement possible).

    Note on confidence recovery:
        CaseResult only stores `confidence_calibration_error = |conf - acc|`
        (signed-absolute), not the raw confidence. We reconstruct mean
        confidence per bin as (mean_acc + mean_err), clamped to [0, 1].
        This is exact when the model is consistently over- or under-confident
        within a bin; mixed-direction error introduces a small bias which is
        acceptable for monitoring at the granularity of R0 dataset sizes.
    """
    if n_bins < 1:
        msg = f"n_bins must be >= 1, got {n_bins}"
        raise ValueError(msg)

    results = list(case_results)
    if not results:
        return 0.0

    bins: list[list[CaseResult]] = [[] for _ in range(n_bins)]
    for r in results:
        bin_idx = min(int(r.factual_accuracy * n_bins), n_bins - 1)
        bins[bin_idx].append(r)

    total = len(results)
    weighted_gap = 0.0
    for bucket in bins:
        if not bucket:
            continue
        bucket_acc = sum(b.factual_accuracy for b in bucket) / len(bucket)
        bucket_conf = bucket_acc + (
            sum(b.confidence_calibration_error for b in bucket) / len(bucket)
        )
        bucket_conf = min(max(bucket_conf, 0.0), 1.0)
        weighted_gap += (len(bucket) / total) * abs(bucket_conf - bucket_acc)

    return round(weighted_gap, 4)
