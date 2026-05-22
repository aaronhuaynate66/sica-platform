"""JSON serialization of a HarnessReport.

We use Pydantic's `model_dump_json` to guarantee schema-stable output that
can be reloaded as HarnessReport for diffing across runs.
"""

from __future__ import annotations

from sica_evals.schemas import HarnessReport


def render_json(report: HarnessReport) -> str:
    """Pretty-printed JSON suitable for both diffing and humans."""
    return report.model_dump_json(indent=2)
