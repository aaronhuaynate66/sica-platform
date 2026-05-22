"""Adapter that drives the real `clinical-extractor` service from the harness.

This wrapper is optional. It only imports `clinical_extractor` lazily so
that `sica-evals` can be installed and tested in environments without
the extractor dependency (e.g. CI runners without an Anthropic API key).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Type-only import. Real module is loaded lazily inside __call__ to
    # keep the dependency optional at runtime.
    pass


class ClinicalExtractorWrapper:
    """Bridges sica-evals.Harness ↔ services/clinical-extractor.

    Usage:
        wrapper = ClinicalExtractorWrapper()
        summary_dict = wrapper(Path("path/to/file.pdf"))
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        env_path: Path | None = None,
    ) -> None:
        """Build the wrapper.

        Parameters
        ----------
        model:
            Optional model override (e.g. 'claude-sonnet-4-5-20250929').
            If None, the extractor uses its default.
        env_path:
            Optional .env file with ANTHROPIC_API_KEY. If None, normal
            environment variable resolution applies.
        """
        self._model = model
        self._env_path = env_path
        self._extractor: Any = None  # type: ignore[no-any-unimported]
        self.extractor_version = "unknown"
        self.model_used = model or "unknown"

    def _lazy_init(self) -> None:
        if self._extractor is not None:
            return
        try:
            from clinical_extractor.extractor import DEFAULT_MODEL, extract_obstetric_summary
        except ImportError as exc:
            msg = (
                "clinical_extractor not installed in this environment. "
                "Install with: pip install -e ./services/clinical-extractor"
            )
            raise RuntimeError(msg) from exc

        if self._env_path and self._env_path.exists():
            from dotenv import load_dotenv

            load_dotenv(self._env_path, override=False)

        self._extract_fn = extract_obstetric_summary
        self.model_used = self._model or DEFAULT_MODEL
        # extractor_version comes from clinical_extractor package metadata
        try:
            import clinical_extractor

            self.extractor_version = getattr(clinical_extractor, "__version__", "unknown")
        except Exception:  # noqa: BLE001 — best-effort metadata
            self.extractor_version = "unknown"
        self._extractor = True

    def __call__(self, pdf_path: Path) -> dict[str, Any]:
        """Run the extractor and return the result as a plain dict.

        We strip the Pydantic shell so downstream comparators don't need to
        import clinical_extractor's schemas.
        """
        self._lazy_init()
        kwargs: dict[str, Any] = {}
        if self._model is not None:
            kwargs["model"] = self._model
        summary = self._extract_fn(pdf_path, **kwargs)
        # ObstetricSummary is a Pydantic v2 model.
        return summary.model_dump(mode="json")  # type: ignore[no-any-return]
