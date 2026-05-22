"""Pydantic schemas for the SICA evaluation harness.

These models are the contract between harness components (comparators,
metrics, reporters). Any incompatible change should be tracked because
reports persisted on disk follow this schema for regression analysis.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Match type taxonomy used across comparators. Documented here as the single
# source of truth.
MatchType = Literal["exact", "fuzzy", "semantic", "missing", "hallucinated", "mismatch"]


class TestCase(BaseModel):
    """A single test case fed to the harness.

    Each case bundles the PDF input, the expected ObstetricSummary as a raw
    dict (no Pydantic dependency on clinical_extractor at this level — we
    keep the harness loosely coupled), and auxiliary metadata.
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    case_id: str = Field(description="Stable identifier, e.g. 'synthetic_case_01'.")
    pdf_path: Path = Field(description="Absolute path to the source PDF document.")
    expected: dict[str, Any] = Field(
        description="Expected ObstetricSummary serialized as dict (from fixtures/*.expected.json).",
    )
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Aux metadata from .meta.json (human_reviewer, baseline_type, etc.).",
    )


class FieldComparison(BaseModel):
    """Outcome of comparing one field between expected and actual."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    field_name: str = Field(description="Dotted name of the field, e.g. 'lab_results[0].value'.")
    expected_value: Any = Field(default=None, description="Expected value (may be None).")
    actual_value: Any = Field(default=None, description="Actual value produced by the extractor.")
    match: bool = Field(description="True iff the comparator considers expected and actual equivalent.")
    match_type: MatchType = Field(description="Categorical reason for the verdict.")
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional confidence score reported by the comparator (e.g. fuzzy ratio).",
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        description="Clinical importance weight used by factual_accuracy. 1.0 = default, 2.0 = critical.",
    )
    notes: str = Field(default="", description="Optional human-readable note.")


class CaseResult(BaseModel):
    """Aggregate result for one TestCase."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    case_id: str
    factual_accuracy: float = Field(ge=0.0, le=1.0)
    critical_omissions: int = Field(ge=0)
    hallucinations: int = Field(ge=0)
    confidence_calibration_error: float = Field(
        default=0.0,
        ge=0.0,
        description="Per-case absolute error between reported confidence and observed accuracy.",
    )
    field_comparisons: list[FieldComparison] = Field(default_factory=list)
    hallucination_descriptions: list[str] = Field(default_factory=list)
    latency_seconds: float = Field(default=0.0, ge=0.0)
    cost_usd: float | None = Field(default=None, ge=0.0)
    timestamp: datetime
    extractor_version: str = Field(default="unknown")
    model_used: str = Field(default="unknown")
    error: str | None = Field(
        default=None,
        description="If the extractor raised, the exception message lives here and metrics are zeroed.",
    )


class HarnessReport(BaseModel):
    """Full harness run output."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    run_id: str
    timestamp: datetime
    cases_total: int = Field(ge=0)
    cases_succeeded: int = Field(ge=0)
    cases_failed: int = Field(ge=0)
    aggregate_metrics: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Aggregate scalars across cases. Keys: factual_accuracy_mean, "
            "critical_omissions_total, hallucinations_total, calibration_error_mean, "
            "latency_seconds_mean."
        ),
    )
    per_case_results: list[CaseResult] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Run-level metadata: extractor identity, host, git commit, etc.",
    )
