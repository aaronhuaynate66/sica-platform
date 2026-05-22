"""Field-level comparators for ObstetricSummary outputs.

Compares two dicts that follow the ObstetricSummary schema and produces a
flat list of FieldComparison records. Weights mark clinically critical
fields so downstream metrics can score them higher.

Design choice: we intentionally avoid importing the clinical_extractor
package. The harness operates on plain dicts (decoded from JSON) and the
ObstetricSummary schema is treated as a known shape, not a Python class.
This keeps `sica-evals` installable without `clinical-extractor` as a
runtime dependency.
"""

from __future__ import annotations

from collections.abc import Iterable
from difflib import SequenceMatcher
from typing import Any

from sica_evals.schemas import FieldComparison

# ---------------------------------------------------------------------------
# Tunable thresholds — single source of truth.
# ---------------------------------------------------------------------------

# Numeric fields tolerance (used for gestational_age_weeks, etc.).
GESTATIONAL_AGE_TOLERANCE_WEEKS = 0.5

# Fuzzy string match threshold. Anything below counts as no-match.
# TODO: replace with semantic similarity via embeddings once a local
# embedding model is available (see ADR 0004 + STRATEGY § 10).
FUZZY_RATIO_THRESHOLD = 0.6

# Fields considered clinically critical. They get weight=2.0 instead of 1.0.
# Validar pesos con líder clínico antes de R1 (TODO).
CRITICAL_FIELDS: set[str] = {
    "patient_age",
    "gestational_age_weeks",
    "fum",
    "fpp",
    "active_problems",
    "risk_factors",
}


# ---------------------------------------------------------------------------
# Primitive comparators
# ---------------------------------------------------------------------------


def _fuzzy_ratio(a: str, b: str) -> float:
    """Return a similarity ratio in [0,1] using difflib."""
    a_norm = a.strip().lower()
    b_norm = b.strip().lower()
    if not a_norm and not b_norm:
        return 1.0
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def _weight_for(field_name: str) -> float:
    """Critical fields get higher weight in factual_accuracy aggregation."""
    base = field_name.split("[")[0].split(".")[0]
    return 2.0 if base in CRITICAL_FIELDS else 1.0


def _compare_optional_scalar(
    field_name: str,
    expected: Any,
    actual: Any,
) -> FieldComparison:
    """Compare two optional scalars (str, int, float, date)."""
    if expected is None and actual is None:
        return FieldComparison(
            field_name=field_name,
            expected_value=None,
            actual_value=None,
            match=True,
            match_type="exact",
            confidence=1.0,
            weight=_weight_for(field_name),
        )
    if expected is None and actual is not None:
        return FieldComparison(
            field_name=field_name,
            expected_value=None,
            actual_value=actual,
            match=False,
            match_type="hallucinated",
            confidence=0.0,
            weight=_weight_for(field_name),
        )
    if expected is not None and actual is None:
        return FieldComparison(
            field_name=field_name,
            expected_value=expected,
            actual_value=None,
            match=False,
            match_type="missing",
            confidence=0.0,
            weight=_weight_for(field_name),
        )
    if expected == actual:
        return FieldComparison(
            field_name=field_name,
            expected_value=expected,
            actual_value=actual,
            match=True,
            match_type="exact",
            confidence=1.0,
            weight=_weight_for(field_name),
        )
    return FieldComparison(
        field_name=field_name,
        expected_value=expected,
        actual_value=actual,
        match=False,
        match_type="mismatch",
        confidence=0.0,
        weight=_weight_for(field_name),
    )


def _compare_gestational_age(
    field_name: str,
    expected: float | None,
    actual: float | None,
) -> FieldComparison:
    """Gestational age compared with ±GESTATIONAL_AGE_TOLERANCE_WEEKS tolerance."""
    if expected is None or actual is None:
        return _compare_optional_scalar(field_name, expected, actual)
    delta = abs(float(expected) - float(actual))
    match = delta <= GESTATIONAL_AGE_TOLERANCE_WEEKS
    return FieldComparison(
        field_name=field_name,
        expected_value=expected,
        actual_value=actual,
        match=match,
        match_type="fuzzy" if match else "mismatch",
        confidence=max(0.0, 1.0 - delta / max(GESTATIONAL_AGE_TOLERANCE_WEEKS, 1.0)),
        weight=_weight_for(field_name),
        notes=f"delta={delta:.2f} weeks; tolerance=±{GESTATIONAL_AGE_TOLERANCE_WEEKS}",
    )


def _compare_string_set(
    field_name: str,
    expected: list[str],
    actual: list[str],
) -> FieldComparison:
    """Compare two lists treated as multi-sets with fuzzy member matching.

    Score = (|matched_expected| + |matched_actual|) / (|expected| + |actual|).
    """
    exp_clean = [s.strip() for s in expected if isinstance(s, str) and s.strip()]
    act_clean = [s.strip() for s in actual if isinstance(s, str) and s.strip()]

    if not exp_clean and not act_clean:
        return FieldComparison(
            field_name=field_name,
            expected_value=expected,
            actual_value=actual,
            match=True,
            match_type="exact",
            confidence=1.0,
            weight=_weight_for(field_name),
        )

    matched_exp = 0
    used_actual: set[int] = set()
    for e in exp_clean:
        best_idx = -1
        best_ratio = 0.0
        for idx, a in enumerate(act_clean):
            if idx in used_actual:
                continue
            r = _fuzzy_ratio(e, a)
            if r > best_ratio:
                best_ratio = r
                best_idx = idx
        if best_ratio >= FUZZY_RATIO_THRESHOLD and best_idx >= 0:
            matched_exp += 1
            used_actual.add(best_idx)

    matched_act = len(used_actual)
    denom = len(exp_clean) + len(act_clean)
    ratio = (matched_exp + matched_act) / denom if denom > 0 else 0.0
    match = ratio >= FUZZY_RATIO_THRESHOLD

    match_type: str
    if match and matched_exp == len(exp_clean) and matched_act == len(act_clean):
        match_type = "exact"
    elif match:
        match_type = "fuzzy"
    elif matched_exp < len(exp_clean):
        match_type = "missing"
    else:
        match_type = "hallucinated"

    return FieldComparison(
        field_name=field_name,
        expected_value=exp_clean,
        actual_value=act_clean,
        match=match,
        match_type=match_type,  # type: ignore[arg-type]
        confidence=ratio,
        weight=_weight_for(field_name),
        notes=f"matched_expected={matched_exp}/{len(exp_clean)}, matched_actual={matched_act}/{len(act_clean)}",
    )


def _compare_notes_summary(
    field_name: str,
    expected: str,
    actual: str,
) -> FieldComparison:
    """Free-text notes summary — fuzzy ratio with threshold.

    TODO: replace with embedding cosine similarity once local embedding
    model is in stack (R1+). The choice of difflib is a stub.
    """
    if not expected and not actual:
        return FieldComparison(
            field_name=field_name,
            expected_value=expected,
            actual_value=actual,
            match=True,
            match_type="exact",
            confidence=1.0,
            weight=_weight_for(field_name),
        )
    if not expected:
        return FieldComparison(
            field_name=field_name,
            expected_value="",
            actual_value=actual,
            match=False,
            match_type="hallucinated",
            confidence=0.0,
            weight=_weight_for(field_name),
        )
    if not actual:
        return FieldComparison(
            field_name=field_name,
            expected_value=expected,
            actual_value="",
            match=False,
            match_type="missing",
            confidence=0.0,
            weight=_weight_for(field_name),
        )
    ratio = _fuzzy_ratio(expected, actual)
    match = ratio >= FUZZY_RATIO_THRESHOLD
    return FieldComparison(
        field_name=field_name,
        expected_value=expected,
        actual_value=actual,
        match=match,
        match_type="fuzzy" if match else "mismatch",
        confidence=ratio,
        weight=_weight_for(field_name),
        notes="difflib ratio (stub — semantic comparison pending, see TODO)",
    )


# ---------------------------------------------------------------------------
# LabResult comparison
# ---------------------------------------------------------------------------


def _lab_key(lab: dict[str, Any]) -> str:
    """Stable key for matching labs across expected/actual."""
    return str(lab.get("name", "")).strip().lower()


def _compare_single_lab(
    field_prefix: str,
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> list[FieldComparison]:
    """Field-by-field comparison of a matched lab pair."""
    comparisons: list[FieldComparison] = []
    for attr in ("name", "value", "unit", "date", "abnormal"):
        cmp_field = f"{field_prefix}.{attr}"
        exp_val = expected.get(attr)
        act_val = actual.get(attr)
        # Abnormal flag is clinically critical when expected is True.
        comp = _compare_optional_scalar(cmp_field, exp_val, act_val)
        if attr == "abnormal" and bool(expected.get("abnormal")):
            comp = comp.model_copy(update={"weight": 2.0})
        comparisons.append(comp)
    return comparisons


def _compare_lab_results(
    field_name: str,
    expected: list[dict[str, Any]],
    actual: list[dict[str, Any]],
) -> list[FieldComparison]:
    """Match labs by name and compare each pair. Unmatched expected => missing.
    Unmatched actual => hallucinated.
    """
    comparisons: list[FieldComparison] = []
    actual_by_key = {_lab_key(lab): lab for lab in actual}
    expected_keys: set[str] = set()

    for idx, exp_lab in enumerate(expected):
        key = _lab_key(exp_lab)
        expected_keys.add(key)
        prefix = f"{field_name}[{idx}:{key}]"
        if key in actual_by_key:
            comparisons.extend(_compare_single_lab(prefix, exp_lab, actual_by_key[key]))
        else:
            comparisons.append(
                FieldComparison(
                    field_name=prefix,
                    expected_value=exp_lab,
                    actual_value=None,
                    match=False,
                    match_type="missing",
                    confidence=0.0,
                    weight=2.0 if exp_lab.get("abnormal") else 1.0,
                    notes="lab present in expected but missing from actual",
                )
            )

    # Hallucinated labs (in actual but not expected)
    for idx, act_lab in enumerate(actual):
        key = _lab_key(act_lab)
        if key not in expected_keys:
            comparisons.append(
                FieldComparison(
                    field_name=f"{field_name}[+{idx}:{key}]",
                    expected_value=None,
                    actual_value=act_lab,
                    match=False,
                    match_type="hallucinated",
                    confidence=0.0,
                    weight=1.0,
                    notes="lab present in actual but not expected",
                )
            )

    return comparisons


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


# Fields compared as plain optional scalars.
_SCALAR_FIELDS: tuple[str, ...] = ("patient_age", "fum", "fpp")

# Fields compared as list-of-strings (multi-set fuzzy).
_STRING_LIST_FIELDS: tuple[str, ...] = ("active_problems", "risk_factors")


def compare_obstetric_summary(
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> list[FieldComparison]:
    """Compare two ObstetricSummary dicts. Returns a flat list of comparisons.

    The returned list is the canonical input to metrics. Order is stable for
    diffing across runs.
    """
    comparisons: list[FieldComparison] = []

    # Scalar fields
    for field in _SCALAR_FIELDS:
        comparisons.append(
            _compare_optional_scalar(field, expected.get(field), actual.get(field))
        )

    # Gestational age (tolerant numeric)
    comparisons.append(
        _compare_gestational_age(
            "gestational_age_weeks",
            expected.get("gestational_age_weeks"),
            actual.get("gestational_age_weeks"),
        )
    )

    # String-list fields (problems, risks)
    for field in _STRING_LIST_FIELDS:
        comparisons.append(
            _compare_string_set(field, expected.get(field) or [], actual.get(field) or [])
        )

    # Lab results
    comparisons.extend(
        _compare_lab_results(
            "lab_results",
            expected.get("lab_results") or [],
            actual.get("lab_results") or [],
        )
    )

    # Notes summary
    comparisons.append(
        _compare_notes_summary(
            "notes_summary",
            expected.get("notes_summary") or "",
            actual.get("notes_summary") or "",
        )
    )

    return comparisons


def critical_field_names(comparisons: Iterable[FieldComparison]) -> list[str]:
    """Return the subset of field_names that the comparator marked as weight>=2.0."""
    return [c.field_name for c in comparisons if c.weight >= 2.0]
