"""Esquemas Pydantic del clinical-extractor.

Estos modelos son el contrato de salida del servicio. Cualquier cambio
incompatible requiere ADR (ver docs/decisions/) porque rompe consumidores
downstream y rompe el harness de evaluación congelado.

Nota: importamos `datetime.date` con alias `_Date` porque uno de los campos
se llama `date` (parte de LabResult). En Python 3.14+ las annotations son
diferidas por PEP 649; el nombre del campo `date` shadow-earía al tipo durante
la resolución de Pydantic.
"""

from datetime import date as _Date

from pydantic import BaseModel, ConfigDict, Field


class EvidenceSpan(BaseModel):
    """Evidencia trazable de una extracción.

    Cada hecho clínico extraído debe poder rastrearse al fragmento exacto
    del documento fuente que lo respalda. Si no hay evidencia explícita,
    el hecho no debería extraerse (devolver None / lista vacía en su lugar).
    """

    model_config = ConfigDict(extra="forbid")

    claim: str = Field(
        description="Hecho extraído al que se refiere esta evidencia. Por ejemplo: 'edad 32 años' o 'Hb 10.8 g/dL'.",
    )
    source_page: int = Field(
        ge=1,
        description="Página del PDF (1-indexed) donde aparece la evidencia.",
    )
    source_text: str = Field(
        min_length=1,
        description="Texto literal, copiado verbatim del documento, que respalda el claim. NO parafrasear.",
    )


class LabResult(BaseModel):
    """Resultado de laboratorio individual."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="Nombre del analito o test. Ejemplos: 'Hemoglobina', 'TSH', 'Glucosa basal'.",
    )
    value: str = Field(
        description="Valor del resultado tal como figura en el documento. Mantener como string para preservar formato original (ej. '10.8', '<0.01', 'No reactivo').",
    )
    unit: str | None = Field(
        default=None,
        description="Unidad del resultado si aplica. Ejemplos: 'g/dL', 'mUI/L', 'mg/dL'. None para tests cualitativos.",
    )
    date: _Date | None = Field(
        default=None,
        description="Fecha del laboratorio en formato ISO (YYYY-MM-DD). None si no está clara en el documento.",
    )
    abnormal: bool | None = Field(
        default=None,
        description="True si el documento marca el resultado como anormal/fuera de rango. False si está dentro de rango. None si no se especifica.",
    )


class ObstetricSummary(BaseModel):
    """Resumen estructurado de una historia clínica obstétrica.

    Este es el output principal del clinical-extractor en R0. La evaluación
    de calidad (STRATEGY § 10, los 7 pilares) se mide contra ground truth
    creado por médicos sobre esta misma estructura.
    """

    model_config = ConfigDict(extra="forbid")

    # ---- Identificación demográfica básica (NO PHI directo) ----
    patient_age: int | None = Field(
        default=None,
        ge=10,
        le=70,
        description="Edad de la paciente en años. None si no consta explícitamente.",
    )

    # ---- Datos gestacionales ----
    gestational_age_weeks: float | None = Field(
        default=None,
        ge=0,
        le=45,
        description="Edad gestacional actual en semanas (puede ser decimal, ej. 28.3). None si no consta o no aplica.",
    )
    fum: _Date | None = Field(
        default=None,
        description="Fecha de última menstruación (FUM) en formato ISO. None si no consta.",
    )
    fpp: _Date | None = Field(
        default=None,
        description="Fecha probable de parto (FPP) en formato ISO. None si no consta o no se puede inferir directamente del documento.",
    )

    # ---- Estado clínico ----
    active_problems: list[str] = Field(
        default_factory=list,
        description="Lista de problemas clínicos activos al momento del documento. Cada problema en una frase breve. Lista vacía si no hay problemas activos consignados.",
    )
    risk_factors: list[str] = Field(
        default_factory=list,
        description="Factores de riesgo obstétricos identificados. Ejemplos: 'Cesárea previa', 'Edad materna avanzada', 'Anemia'.",
    )
    lab_results: list[LabResult] = Field(
        default_factory=list,
        description="Laboratorios disponibles en el documento. Lista vacía si no hay laboratorios.",
    )
    notes_summary: str = Field(
        default="",
        description="Resumen narrativo de la evolución, en 2-4 oraciones. Si no hay información suficiente, devolver string vacío.",
    )

    # ---- Calidad de la extracción ----
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Puntaje de confianza global de la extracción (0.0 a 1.0). Bajo si el documento es ambiguo, fragmentado, mal escaneado, o si campos críticos no estaban claros.",
    )
    evidence_spans: list[EvidenceSpan] = Field(
        default_factory=list,
        description="Spans de evidencia que respaldan los hechos extraídos. Idealmente uno por campo no trivial. Lista vacía solo si todo el documento fue genérico y no hubo extracciones específicas.",
    )
