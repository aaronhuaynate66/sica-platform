"""Mock extractor for offline testing.

Returns a pre-canned ObstetricSummary dict by case_id. Used by unit tests
and CI so the harness can exercise the full pipeline without an API key.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class MockExtractor:
    """Callable returning fixed outputs from an in-memory map."""

    def __init__(self, outputs_by_path: dict[Path, dict[str, Any]] | None = None) -> None:
        self._outputs: dict[str, dict[str, Any]] = {
            str(p): v for p, v in (outputs_by_path or {}).items()
        }
        self.calls: list[Path] = []
        self.extractor_version = "mock-0.1.0"
        self.model_used = "mock"

    def register(self, pdf_path: Path, output: dict[str, Any]) -> None:
        self._outputs[str(pdf_path)] = output

    def __call__(self, pdf_path: Path) -> dict[str, Any]:
        self.calls.append(pdf_path)
        key = str(pdf_path)
        if key not in self._outputs:
            msg = f"MockExtractor has no registered output for {pdf_path}"
            raise KeyError(msg)
        return self._outputs[key]
