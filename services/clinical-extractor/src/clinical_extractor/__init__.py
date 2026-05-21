"""clinical-extractor — extracción estructurada de historias clínicas obstétricas.

Primera capa de la Multimodal Ingestion Layer de SICA (STRATEGY § 6.3).
Convierte PDFs nativos en objetos Pydantic validados con evidencia trazable.
"""

from clinical_extractor.extractor import extract_from_pdf
from clinical_extractor.schemas import EvidenceSpan, LabResult, ObstetricSummary

__version__ = "0.1.0"

__all__ = [
    "EvidenceSpan",
    "LabResult",
    "ObstetricSummary",
    "__version__",
    "extract_from_pdf",
]
