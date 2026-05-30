"""Métricas de comparación entre dos versiones de prompt sobre el mismo PDF.

Diseñado para validar que una versión candidata (v_b) NO regresiona métricas
clínicas críticas vs. la versión actual en producción (v_a) antes de promoverla
a default en ``DEFAULT_VERSIONS``.

Convenciones:
    - Las métricas son comparativas (no absolutas). No miden "qué tan correcto
      es v2" contra ground truth; eso es responsabilidad del harness/baseline.
      Aquí solo medimos delta v2 - v1 en ejes operativos.
    - El sufijo ``_v1`` en los campos refiere a ``version_a`` (la baseline en
      esta comparación), y ``_v2`` a ``version_b`` (la candidata). Los números
      reales (1, 2) NO están hardcodeados: el comparator soporta cualquier par
      de versiones.
    - Texto libre se compara con Jaccard de keywords (no embeddings) — barato
      y determinístico. Suficiente para detectar pérdida masiva de contenido,
      no para juicio semántico fino.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

# Tolerancia para edad gestacional en semanas. Coincide con el threshold que
# usa ``field_comparator`` para considerar dos GA "equivalentes". Mantenerlo
# en una constante facilita auditar el contrato.
GA_TOLERANCE_WEEKS = 0.5

# Tolerancia de confidence_score para no marcar como regresión cambios menores.
CONFIDENCE_DELTA_TOLERANCE = 0.05

# Stopwords mínimos en español. No exhaustivo; basta para reducir ruido al
# extraer keywords de notes_summary.
_SPANISH_STOPWORDS = frozenset(
    {
        "de", "la", "el", "en", "y", "a", "con", "por", "un", "una",
        "los", "las", "del", "al", "se", "que", "para", "es", "su",
        "lo", "le", "sin", "como", "más", "mas", "pero", "ya", "no",
        "sus", "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas",
        "o", "u", "e", "ha", "han", "fue", "son", "ser", "está",
    }
)


@dataclass(frozen=True)
class ComparisonMetrics:
    """Métricas agregadas de la comparación de 1 caso.

    Cada instancia representa un único PDF/caso comparado entre dos
    versiones del prompt. Los listados ``regressions``/``improvements``
    contienen nombres de campos donde el comparator detectó cambio
    cualitativo; ``neutral_changes`` cambios cuantificables pero sin
    veredicto (e.g. costo).
    """

    case_id: str

    # ---- Identidad numérica/cronológica ----
    patient_age_match: bool
    gestational_age_match: bool  # con tolerancia ±GA_TOLERANCE_WEEKS
    fum_match: bool
    fpp_match: bool

    # ---- Active problems ----
    active_problems_v1: list[str]
    active_problems_v2: list[str]
    active_problems_overlap: float  # Jaccard 0.0-1.0
    active_problems_added: list[str]  # presentes en v2 y NO en v1
    active_problems_removed: list[str]  # presentes en v1 y NO en v2

    # ---- Risk factors ----
    risk_factors_v1: list[str]
    risk_factors_v2: list[str]
    risk_factors_overlap: float

    # ---- Cuantitativos ----
    confidence_score_v1: float
    confidence_score_v2: float
    confidence_delta: float

    lab_results_count_v1: int
    lab_results_count_v2: int

    evidence_spans_count_v1: int
    evidence_spans_count_v2: int

    # ---- Económicos (opcionales — pueden ser None si no hay metadata) ----
    cost_v1_usd: float | None
    cost_v2_usd: float | None
    cost_delta_usd: float | None

    latency_v1_ms: int | None
    latency_v2_ms: int | None
    latency_delta_ms: int | None

    # ---- Texto libre ----
    notes_summary_length_v1: int
    notes_summary_length_v2: int
    notes_summary_keyword_overlap: float  # Jaccard de keywords top-N

    # ---- Veredicto por caso ----
    regressions: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    neutral_changes: list[str] = field(default_factory=list)


def compute_jaccard(set_a: set[str], set_b: set[str]) -> float:
    """Jaccard similarity de dos sets de strings (case-insensitive, trimmed).

    Returns:
        - 1.0 si ambos sets son iguales (incluso si ambos están vacíos).
        - 0.0 si son disjuntos no vacíos.
        - len(A intersect B) / len(A union B) en otro caso.

    Notas:
        - Lowercase y strip se aplican antes de comparar.
        - Implementación intencionalmente simple — para texto libre largo
          conviene usar overlap de keywords (ver ``extract_keywords``).
    """
    a_lower = {x.lower().strip() for x in set_a}
    b_lower = {x.lower().strip() for x in set_b}
    if not a_lower and not b_lower:
        return 1.0
    inter = a_lower & b_lower
    union = a_lower | b_lower
    if not union:
        return 1.0
    return len(inter) / len(union)


def extract_keywords(text: str, top_n: int = 20) -> set[str]:
    """Extrae las top-N palabras clave de un texto.

    Heurística:
        - Tokenización con ``\\b[a-záéíóúñ]+\\b`` (lowercase). Acepta tildes y ñ.
        - Excluye stopwords en español y tokens de ≤2 caracteres.
        - Ordena por frecuencia y toma los top-N únicos.

    Pensado para texto libre tipo ``notes_summary``. Para textos muy cortos
    (<5 palabras) puede devolver < N keywords; es esperado.
    """
    if not text:
        return set()
    words = re.findall(r"\b[a-záéíóúñ]+\b", text.lower())
    words = [w for w in words if w not in _SPANISH_STOPWORDS and len(w) > 2]
    if not words:
        return set()
    counter = Counter(words)
    return {w for w, _ in counter.most_common(top_n)}


def _as_float(value: Any, default: float = 0.0) -> float:
    """Coerce a float aceptando ``None`` y strings numéricos."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int_list(items: Any) -> list[str]:
    """Coerce a list[str], filtrando None y tipos no string."""
    if not items:
        return []
    return [str(x) for x in items if x is not None]


def compare_outputs(
    case_id: str,
    output_v1: dict[str, Any],
    output_v2: dict[str, Any],
    metadata_v1: dict[str, Any] | None = None,
    metadata_v2: dict[str, Any] | None = None,
) -> ComparisonMetrics:
    """Compara dos outputs ``ObstetricSummary`` del mismo caso.

    Args:
        case_id: Identificador del caso (e.g. ``"longitudinal_lucia_sem16"``).
        output_v1: Output del prompt baseline, como dict (no Pydantic model).
        output_v2: Output del prompt candidato, como dict.
        metadata_v1: Metadata operacional opcional (``cost_usd``, ``latency_ms``).
        metadata_v2: Metadata operacional opcional para v2.

    Returns:
        ComparisonMetrics inmutable con todos los campos calculados.
    """
    # Identidad numérica/cronológica
    patient_age_match = output_v1.get("patient_age") == output_v2.get("patient_age")
    ga_v1 = _as_float(output_v1.get("gestational_age_weeks"))
    ga_v2 = _as_float(output_v2.get("gestational_age_weeks"))
    gestational_age_match = abs(ga_v1 - ga_v2) <= GA_TOLERANCE_WEEKS

    fum_match = output_v1.get("fum") == output_v2.get("fum")
    fpp_match = output_v1.get("fpp") == output_v2.get("fpp")

    # Active problems
    ap_v1 = _as_int_list(output_v1.get("active_problems"))
    ap_v2 = _as_int_list(output_v2.get("active_problems"))
    ap_overlap = compute_jaccard(set(ap_v1), set(ap_v2))
    ap_v1_lower = {x.lower().strip() for x in ap_v1}
    ap_v2_lower = {x.lower().strip() for x in ap_v2}
    ap_added = [x for x in ap_v2 if x.lower().strip() not in ap_v1_lower]
    ap_removed = [x for x in ap_v1 if x.lower().strip() not in ap_v2_lower]

    # Risk factors
    rf_v1 = _as_int_list(output_v1.get("risk_factors"))
    rf_v2 = _as_int_list(output_v2.get("risk_factors"))
    rf_overlap = compute_jaccard(set(rf_v1), set(rf_v2))

    # Cuantitativos
    conf_v1 = _as_float(output_v1.get("confidence_score"))
    conf_v2 = _as_float(output_v2.get("confidence_score"))
    lab_v1 = len(output_v1.get("lab_results") or [])
    lab_v2 = len(output_v2.get("lab_results") or [])
    ev_v1 = len(output_v1.get("evidence_spans") or [])
    ev_v2 = len(output_v2.get("evidence_spans") or [])

    # Costo / latencia (opcional)
    cost_v1: float | None = None
    cost_v2: float | None = None
    lat_v1: int | None = None
    lat_v2: int | None = None
    if metadata_v1 is not None:
        raw_cost = metadata_v1.get("cost_usd")
        cost_v1 = float(raw_cost) if raw_cost is not None else None
        raw_lat = metadata_v1.get("latency_ms")
        lat_v1 = int(raw_lat) if raw_lat is not None else None
    if metadata_v2 is not None:
        raw_cost = metadata_v2.get("cost_usd")
        cost_v2 = float(raw_cost) if raw_cost is not None else None
        raw_lat = metadata_v2.get("latency_ms")
        lat_v2 = int(raw_lat) if raw_lat is not None else None

    cost_delta = (cost_v2 - cost_v1) if (cost_v1 is not None and cost_v2 is not None) else None
    lat_delta = (lat_v2 - lat_v1) if (lat_v1 is not None and lat_v2 is not None) else None

    # Texto libre
    notes_v1 = output_v1.get("notes_summary") or ""
    notes_v2 = output_v2.get("notes_summary") or ""
    kw_overlap = compute_jaccard(extract_keywords(notes_v1), extract_keywords(notes_v2))

    # ---------------- Veredicto ----------------
    # Regression: se PIERDE algo crítico (identidad numérica, evidence, labs,
    # confidence). El umbral del 30% para evidence/labs proviene del criterio
    # de "no degradar trazabilidad mas allá de ruido natural de muestreo".
    regressions: list[str] = []
    improvements: list[str] = []
    neutral: list[str] = []

    if not patient_age_match:
        regressions.append("patient_age")
    if not gestational_age_match:
        regressions.append("gestational_age_weeks")
    if not fum_match:
        regressions.append("fum")
    if not fpp_match:
        regressions.append("fpp")

    if conf_v2 < conf_v1 - CONFIDENCE_DELTA_TOLERANCE:
        regressions.append("confidence_score")
    elif conf_v2 > conf_v1 + CONFIDENCE_DELTA_TOLERANCE:
        improvements.append("confidence_score")

    if ev_v1 > 0 and ev_v2 < ev_v1 * 0.7:
        regressions.append("evidence_spans_count")
    if lab_v1 > 0 and lab_v2 < lab_v1 * 0.7:
        regressions.append("lab_results_count")

    # Improvement: active_problems con alta overlap conceptual pero más
    # conciso → v2 limpió el ruido sin perder contenido. Esto es exactamente
    # el cambio que motivó v2 (eliminar "Embarazo de N semanas" que no es
    # un problema activo).
    if ap_overlap >= 0.5 and len(ap_v2) < len(ap_v1) and ap_removed:
        improvements.append("active_problems_conciseness")
    if rf_overlap < 0.5 and len(rf_v1) > 0:
        # Cambio mayor en risk_factors sin overlap: neutral, requiere review.
        neutral.append("risk_factors_divergence")

    if kw_overlap < 0.3 and notes_v1 and notes_v2:
        # Notes_summary cambió radicalmente — neutral porque no podemos
        # juzgar la dirección del cambio con Jaccard de keywords solo.
        neutral.append("notes_summary_keyword_divergence")

    if cost_delta is not None and abs(cost_delta) > 0.001:
        neutral.append("cost_usd")
    if lat_delta is not None and abs(lat_delta) > 500:
        neutral.append("latency_ms")

    return ComparisonMetrics(
        case_id=case_id,
        patient_age_match=patient_age_match,
        gestational_age_match=gestational_age_match,
        fum_match=fum_match,
        fpp_match=fpp_match,
        active_problems_v1=ap_v1,
        active_problems_v2=ap_v2,
        active_problems_overlap=ap_overlap,
        active_problems_added=ap_added,
        active_problems_removed=ap_removed,
        risk_factors_v1=rf_v1,
        risk_factors_v2=rf_v2,
        risk_factors_overlap=rf_overlap,
        confidence_score_v1=conf_v1,
        confidence_score_v2=conf_v2,
        confidence_delta=conf_v2 - conf_v1,
        lab_results_count_v1=lab_v1,
        lab_results_count_v2=lab_v2,
        evidence_spans_count_v1=ev_v1,
        evidence_spans_count_v2=ev_v2,
        cost_v1_usd=cost_v1,
        cost_v2_usd=cost_v2,
        cost_delta_usd=cost_delta,
        latency_v1_ms=lat_v1,
        latency_v2_ms=lat_v2,
        latency_delta_ms=lat_delta,
        notes_summary_length_v1=len(notes_v1),
        notes_summary_length_v2=len(notes_v2),
        notes_summary_keyword_overlap=kw_overlap,
        regressions=regressions,
        improvements=improvements,
        neutral_changes=neutral,
    )
