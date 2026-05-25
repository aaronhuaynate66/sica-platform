"""Harness orchestrator.

Loads test cases from a fixtures directory, runs an extractor over each
case, compares results against expected output, aggregates metrics into
a HarnessReport, and persists reports to disk in selected formats.

Determinism: the harness itself adds no randomness. Non-determinism
comes from the wrapped extractor (e.g. LLM sampling without seed).
"""

from __future__ import annotations

import json
import platform
import socket
import subprocess
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sica_evals.comparators import compare_obstetric_summary
from sica_evals.metrics import (
    compute_calibration_error,
    compute_factual_accuracy,
    count_critical_omissions,
    detect_hallucinations,
)
from sica_evals.metrics.calibration import compute_case_calibration_error
from sica_evals.reporters import render_html, render_json, render_markdown
from sica_evals.schemas import CaseResult, HarnessReport, TestCase

ExtractorCallable = Callable[[Path], dict[str, Any]]

# Supported report formats. Order matters for default 'all' behavior.
SUPPORTED_FORMATS: tuple[str, ...] = ("json", "markdown", "html")


def _git_commit_short(repo_root: Path) -> str:
    """Best-effort short git hash. Returns 'unknown' if not in a repo or git missing."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return "unknown"
    return result.stdout.strip() or "unknown"


class Harness:
    """End-to-end runner. One Harness == one extractor + one fixtures_dir."""

    def __init__(
        self,
        extractor_callable: ExtractorCallable,
        fixtures_dir: Path,
        output_dir: Path,
        *,
        extractor_version: str = "unknown",
        model_used: str = "unknown",
    ) -> None:
        self.extractor = extractor_callable
        self.fixtures_dir = fixtures_dir.resolve()
        self.output_dir = output_dir.resolve()
        self.extractor_version = extractor_version
        self.model_used = model_used

    # ------------------------------------------------------------------
    # Test case loading
    # ------------------------------------------------------------------

    def load_test_cases(self, *, filter_case_id: str | None = None) -> list[TestCase]:
        """Discover all *.expected.json fixtures and build TestCase records.

        Convention:
          - {case_id}.expected.json — expected ObstetricSummary
          - {case_id}.expected.meta.json — auxiliary metadata (optional)
          - PDF path is taken from meta.pdf_source.path if present;
            otherwise inferred relative to repo root.
        """
        if not self.fixtures_dir.exists():
            msg = f"fixtures_dir does not exist: {self.fixtures_dir}"
            raise FileNotFoundError(msg)

        repo_root = self._infer_repo_root()
        cases: list[TestCase] = []
        for expected_path in sorted(self.fixtures_dir.glob("*.expected.json")):
            case_id = expected_path.name.removesuffix(".expected.json")
            if filter_case_id and case_id != filter_case_id:
                continue

            expected = json.loads(expected_path.read_text(encoding="utf-8"))
            meta_path = self.fixtures_dir / f"{case_id}.expected.meta.json"
            meta: dict[str, Any] = {}
            pdf_path: Path | None = None
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                pdf_source = meta.get("pdf_source") or {}
                if pdf_source.get("path"):
                    pdf_path = (repo_root / pdf_source["path"]).resolve()
            if pdf_path is None:
                # Fallback: look for {case_id}.pdf next to fixtures.
                guess = self.fixtures_dir / f"{case_id}.pdf"
                pdf_path = guess if guess.exists() else self.fixtures_dir / f"{case_id}.pdf"

            cases.append(
                TestCase(
                    case_id=case_id,
                    pdf_path=pdf_path,
                    expected=expected,
                    meta=meta,
                )
            )

        return cases

    def _infer_repo_root(self) -> Path:
        """Heuristic: walk up from fixtures_dir until we find a .git directory."""
        cur = self.fixtures_dir
        for _ in range(10):
            if (cur / ".git").exists():
                return cur
            if cur.parent == cur:
                break
            cur = cur.parent
        # Fallback: 2 levels above fixtures_dir.
        return self.fixtures_dir.parent.parent

    # ------------------------------------------------------------------
    # Single-case execution
    # ------------------------------------------------------------------

    def run_case(self, case: TestCase) -> CaseResult:
        """Execute the extractor on one case and compute its metrics."""
        started = time.perf_counter()
        timestamp = datetime.now(UTC)

        try:
            actual = self.extractor(case.pdf_path)
        except Exception as exc:
            elapsed = time.perf_counter() - started
            return CaseResult(
                case_id=case.case_id,
                factual_accuracy=0.0,
                critical_omissions=0,
                hallucinations=0,
                confidence_calibration_error=0.0,
                field_comparisons=[],
                hallucination_descriptions=[],
                latency_seconds=elapsed,
                timestamp=timestamp,
                extractor_version=self.extractor_version,
                model_used=self.model_used,
                error=f"{type(exc).__name__}: {exc}",
            )

        elapsed = time.perf_counter() - started

        comparisons = compare_obstetric_summary(case.expected, actual)
        accuracy = compute_factual_accuracy(comparisons)
        omissions = count_critical_omissions(comparisons)
        hallucinations = detect_hallucinations(comparisons)
        reported_confidence = float(actual.get("confidence_score") or 0.0)
        calib_err = compute_case_calibration_error(reported_confidence, accuracy)

        return CaseResult(
            case_id=case.case_id,
            factual_accuracy=accuracy,
            critical_omissions=omissions,
            hallucinations=len(hallucinations),
            confidence_calibration_error=calib_err,
            field_comparisons=comparisons,
            hallucination_descriptions=hallucinations,
            latency_seconds=elapsed,
            timestamp=timestamp,
            extractor_version=self.extractor_version,
            model_used=self.model_used,
        )

    # ------------------------------------------------------------------
    # Full run
    # ------------------------------------------------------------------

    def run_all(self, *, filter_case_id: str | None = None) -> HarnessReport:
        """Run every test case found in fixtures_dir and aggregate."""
        cases = self.load_test_cases(filter_case_id=filter_case_id)
        results: list[CaseResult] = [self.run_case(c) for c in cases]

        succeeded = sum(1 for r in results if r.error is None)
        failed = len(results) - succeeded

        aggregate: dict[str, float] = {
            "factual_accuracy_mean": (
                round(sum(r.factual_accuracy for r in results) / max(len(results), 1), 4)
            ),
            "critical_omissions_total": float(sum(r.critical_omissions for r in results)),
            "hallucinations_total": float(sum(r.hallucinations for r in results)),
            "calibration_error_mean": compute_calibration_error(results),
            "latency_seconds_mean": (
                round(sum(r.latency_seconds for r in results) / max(len(results), 1), 4)
            ),
        }

        repo_root = self._infer_repo_root()
        metadata: dict[str, Any] = {
            "host": socket.gethostname(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "git_commit": _git_commit_short(repo_root),
            "extractor_version": self.extractor_version,
            "model_used": self.model_used,
            "fixtures_dir": str(self.fixtures_dir),
        }

        return HarnessReport(
            run_id=str(uuid.uuid4()),
            timestamp=datetime.now(UTC),
            cases_total=len(results),
            cases_succeeded=succeeded,
            cases_failed=failed,
            aggregate_metrics=aggregate,
            per_case_results=results,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Report persistence
    # ------------------------------------------------------------------

    def save_report(
        self,
        report: HarnessReport,
        formats: list[str] | tuple[str, ...] = ("json",),
    ) -> dict[str, Path]:
        """Persist the report under output_dir. Returns format -> file path."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        ts = report.timestamp.strftime("%Y%m%dT%H%M%SZ")
        base = self.output_dir / f"{ts}_{report.run_id[:8]}"
        written: dict[str, Path] = {}

        if "all" in formats:
            formats = SUPPORTED_FORMATS

        for fmt in formats:
            if fmt == "json":
                path = base.with_suffix(".json")
                path.write_text(render_json(report), encoding="utf-8")
                written["json"] = path
            elif fmt == "markdown":
                path = base.with_suffix(".md")
                path.write_text(render_markdown(report), encoding="utf-8")
                written["markdown"] = path
            elif fmt == "html":
                path = base.with_suffix(".html")
                path.write_text(render_html(report), encoding="utf-8")
                written["html"] = path
            else:
                msg = f"Unsupported report format: {fmt!r}. Supported: {SUPPORTED_FORMATS}"
                raise ValueError(msg)

        return written


# ----------------------------------------------------------------------
# Cross-run diff (issue #10 criterion: comparator between runs)
# ----------------------------------------------------------------------


def diff_reports(report_a: HarnessReport, report_b: HarnessReport) -> dict[str, Any]:
    """Compute a delta between two HarnessReports.

    Positive deltas mean B improved over A. Useful to gate PRs and detect
    silent regressions when a prompt or model version changes.
    """
    deltas: dict[str, Any] = {
        "run_a": report_a.run_id,
        "run_b": report_b.run_id,
        "timestamp_a": report_a.timestamp.isoformat(),
        "timestamp_b": report_b.timestamp.isoformat(),
        "aggregate_delta": {},
        "per_case_delta": [],
    }

    keys = set(report_a.aggregate_metrics) | set(report_b.aggregate_metrics)
    for k in sorted(keys):
        va = report_a.aggregate_metrics.get(k, 0.0)
        vb = report_b.aggregate_metrics.get(k, 0.0)
        deltas["aggregate_delta"][k] = round(vb - va, 4)

    by_a = {r.case_id: r for r in report_a.per_case_results}
    by_b = {r.case_id: r for r in report_b.per_case_results}
    for case_id in sorted(set(by_a) | set(by_b)):
        ra = by_a.get(case_id)
        rb = by_b.get(case_id)
        deltas["per_case_delta"].append(
            {
                "case_id": case_id,
                "factual_accuracy_delta": round(
                    (rb.factual_accuracy if rb else 0.0)
                    - (ra.factual_accuracy if ra else 0.0),
                    4,
                ),
                "critical_omissions_delta": (
                    (rb.critical_omissions if rb else 0)
                    - (ra.critical_omissions if ra else 0)
                ),
                "hallucinations_delta": (
                    (rb.hallucinations if rb else 0)
                    - (ra.hallucinations if ra else 0)
                ),
            }
        )

    return deltas
