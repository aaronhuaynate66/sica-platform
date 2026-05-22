"""Evidence span comparator.

Verifies that EvidenceSpan entries:
  - have a `source_text` that literally exists in the source PDF text;
  - cover a claim that matches one of the expected claims (fuzzy);
  - have Jaccard overlap with expected spans above a threshold.

The PDF text is provided externally (extracted by the harness with pypdf
or whatever the extractor used). The comparator does NOT re-parse PDFs.
"""

from __future__ import annotations

from collections.abc import Iterable
from difflib import SequenceMatcher
from typing import Any

from sica_evals.schemas import FieldComparison

# Minimum Jaccard token-overlap to consider two spans equivalent.
SPAN_JACCARD_THRESHOLD = 0.4

# Minimum fuzzy ratio between expected and actual claim text.
CLAIM_FUZZY_THRESHOLD = 0.6


def _norm_tokens(text: str) -> set[str]:
    """Lowercase tokenization for Jaccard overlap. Empty set on empty input."""
    return {tok for tok in text.lower().replace("\n", " ").split() if tok}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def span_in_text(span_text: str, pdf_text: str | None) -> bool:
    """Return True iff `span_text` (whitespace-normalized) appears in `pdf_text`.

    If `pdf_text` is None or empty (e.g. when we don't have the source text
    available), returns True conservatively — the comparator cannot prove
    absence. This is logged but not failed.
    """
    if not pdf_text:
        return True
    haystack = " ".join(pdf_text.split()).lower()
    needle = " ".join(span_text.split()).lower()
    if not needle:
        return False
    return needle in haystack


def compare_evidence_spans(
    expected_spans: list[dict[str, Any]],
    actual_spans: list[dict[str, Any]],
    *,
    pdf_text: str | None = None,
) -> list[FieldComparison]:
    """Compare two lists of EvidenceSpan dicts.

    For each expected span we look for a best-matching actual span by claim
    fuzzy ratio, then verify Jaccard overlap on source_text and presence in
    the PDF text. Unmatched expected => missing. Unmatched actual that fail
    PDF presence check => hallucinated.
    """
    comparisons: list[FieldComparison] = []

    used_actual: set[int] = set()

    for e_idx, exp_span in enumerate(expected_spans):
        exp_claim = str(exp_span.get("claim", "")).strip()
        exp_text = str(exp_span.get("source_text", "")).strip()
        best_idx = -1
        best_ratio = 0.0
        for a_idx, act_span in enumerate(actual_spans):
            if a_idx in used_actual:
                continue
            ratio = SequenceMatcher(
                None, exp_claim.lower(), str(act_span.get("claim", "")).lower()
            ).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_idx = a_idx

        if best_ratio < CLAIM_FUZZY_THRESHOLD or best_idx < 0:
            comparisons.append(
                FieldComparison(
                    field_name=f"evidence_spans[{e_idx}]",
                    expected_value=exp_span,
                    actual_value=None,
                    match=False,
                    match_type="missing",
                    confidence=best_ratio,
                    weight=1.0,
                    notes="no actual span matched expected claim above threshold",
                )
            )
            continue

        used_actual.add(best_idx)
        act_span = actual_spans[best_idx]
        act_text = str(act_span.get("source_text", "")).strip()

        # Jaccard on source_text
        jacc = _jaccard(_norm_tokens(exp_text), _norm_tokens(act_text))

        # Presence in PDF
        present = span_in_text(act_text, pdf_text)

        match = jacc >= SPAN_JACCARD_THRESHOLD and present
        match_type = (
            "exact"
            if act_text.lower() == exp_text.lower() and present
            else ("fuzzy" if match else "mismatch")
        )

        comparisons.append(
            FieldComparison(
                field_name=f"evidence_spans[{e_idx}]",
                expected_value=exp_span,
                actual_value=act_span,
                match=match,
                match_type=match_type,  # type: ignore[arg-type]
                confidence=jacc,
                weight=1.0,
                notes=(
                    f"claim_ratio={best_ratio:.2f}, jaccard={jacc:.2f}, "
                    f"present_in_pdf={present}"
                ),
            )
        )

    # Hallucinated actual spans: not matched to any expected AND not present in pdf.
    for a_idx, act_span in enumerate(actual_spans):
        if a_idx in used_actual:
            continue
        act_text = str(act_span.get("source_text", "")).strip()
        present = span_in_text(act_text, pdf_text)
        comparisons.append(
            FieldComparison(
                field_name=f"evidence_spans[+{a_idx}]",
                expected_value=None,
                actual_value=act_span,
                match=False,
                match_type="hallucinated" if not present else "fuzzy",
                confidence=0.0 if not present else 0.5,
                weight=1.0,
                notes=(
                    "extra actual span unmatched in expected; "
                    f"present_in_pdf={present}"
                ),
            )
        )

    return comparisons


def find_unsupported_spans(
    spans: Iterable[dict[str, Any]],
    pdf_text: str | None,
) -> list[dict[str, Any]]:
    """Return spans whose source_text is NOT verbatim in the PDF text.

    Useful as a fast hallucination probe independent of expected baseline.
    """
    if not pdf_text:
        return []
    bad: list[dict[str, Any]] = []
    for s in spans:
        text = str(s.get("source_text", "")).strip()
        if text and not span_in_text(text, pdf_text):
            bad.append(s)
    return bad
