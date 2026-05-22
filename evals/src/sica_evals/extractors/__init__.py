"""Extractor adapters that the harness can drive.

An extractor is any callable that maps Path[PDF] -> ObstetricSummary.
"""

from sica_evals.extractors.clinical_extractor_wrapper import ClinicalExtractorWrapper
from sica_evals.extractors.mock_extractor import MockExtractor

__all__ = ["ClinicalExtractorWrapper", "MockExtractor"]
