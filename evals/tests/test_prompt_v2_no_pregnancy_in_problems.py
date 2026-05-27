"""Tests de regresión para ``extract_obstetric_v2``.

v2 corrige un anti-patrón clínico observado en v1: "Embarazo de N
semanas + N días por FUR" aparecía en ``active_problems`` (visible en
``evals/fixtures/longitudinal_lucia/sem16/extracted.json``). v2 agrega
la regla 8 al system prompt prohibiendo explícitamente esa práctica.

Estos tests cargan ``extracted_v2.json`` (output real de v2 contra los
4 PDFs longitudinales de Lucía, commiteado como fixture en esta sesión).
NO disparan extracciones nuevas — costoso y no determinista.

Patrón mirror del existente ``test_longitudinal_continuity.py``: misma
fixture-loader strategy, scope module, JSONs cargados una sola vez.

Ver ADR-0008 § Actualización 2026-05-27.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


def _fixtures_root() -> Path:
    return Path(__file__).resolve().parent.parent / "fixtures" / "longitudinal_lucia"


@pytest.fixture(scope="module")
def extracted_v2() -> dict[int, dict]:
    """Devuelve dict ``{16: v2_json, 24: ..., 32: ..., 38: ...}``."""
    root = _fixtures_root()
    out: dict[int, dict] = {}
    for sem in (16, 24, 32, 38):
        path = root / f"sem{sem}" / "extracted_v2.json"
        if not path.exists():
            msg = (
                f"Falta extracted_v2.json para sem{sem}: {path}. "
                "Regenerar con `clinical-extractor extract ... --prompt-version 2`."
            )
            raise FileNotFoundError(msg)
        out[sem] = json.loads(path.read_text(encoding="utf-8"))
    return out


@pytest.fixture(scope="module")
def extracted_v1() -> dict[int, dict]:
    """Misma carga pero del ``extracted.json`` (v1) para comparaciones."""
    root = _fixtures_root()
    out: dict[int, dict] = {}
    for sem in (16, 24, 32, 38):
        path = root / f"sem{sem}" / "extracted.json"
        out[sem] = json.loads(path.read_text(encoding="utf-8"))
    return out


# Pattern para detectar "Embarazo de N semanas..." y variantes. El objetivo
# es capturar el anti-patrón exacto observado en sem16/v1 más sus mutaciones
# previsibles. Case-insensitive.
_PREGNANCY_AS_PROBLEM_PATTERNS = (
    re.compile(r"\bembarazo\s+de\s+\d", re.IGNORECASE),
    re.compile(r"\bembarazo\s+activo\b", re.IGNORECASE),
    re.compile(r"\bembarazo\s+a\s+término\b", re.IGNORECASE),
    re.compile(r"\bgestaci[oó]n\s+de\s+\d", re.IGNORECASE),
)


def _problem_mentions_pregnancy_as_problem(problem: str) -> bool:
    return any(p.search(problem) for p in _PREGNANCY_AS_PROBLEM_PATTERNS)


# =========================================================================
# Anti-patrón eliminado: "Embarazo de N semanas..." en active_problems
# =========================================================================


def test_v2_sem16_no_pregnancy_in_active_problems(extracted_v2) -> None:
    """sem16 era el caso testigo: v1 incluía 'Embarazo de 16 semanas + 2
    días por FUR'. v2 debe eliminarlo."""
    problems = extracted_v2[16].get("active_problems", []) or []
    for p in problems:
        assert not _problem_mentions_pregnancy_as_problem(str(p)), (
            f"sem16 v2 active_problems sigue conteniendo el anti-patrón "
            f"'embarazo como problema': '{p}'"
        )
    # Sobrepeso pre-gestacional sigue siendo problema válido en sem16
    # (factor que se está siguiendo activamente). Confirmamos que NO
    # desapareció en el cleanup.
    text = " ".join(str(p).lower() for p in problems)
    assert "sobrepeso" in text, (
        f"sem16 v2 perdió 'sobrepeso' de active_problems: {problems}"
    )


def test_v2_sem24_no_pregnancy_in_active_problems(extracted_v2) -> None:
    """sem24 v1 no tenía 'embarazo' pero validamos contrato uniforme."""
    problems = extracted_v2[24].get("active_problems", []) or []
    for p in problems:
        assert not _problem_mentions_pregnancy_as_problem(str(p)), (
            f"sem24 v2 contiene anti-patrón 'embarazo como problema': '{p}'"
        )
    # Diabetes gestacional debe estar — el dato clínico crítico de sem24.
    text = " ".join(str(p).lower() for p in problems)
    assert "diabetes" in text, (
        f"sem24 v2 perdió DG de active_problems: {problems}"
    )


def test_v2_sem32_no_pregnancy_in_active_problems(extracted_v2) -> None:
    """sem32: DG mal controlada + macrosomía incipiente preservados."""
    problems = extracted_v2[32].get("active_problems", []) or []
    for p in problems:
        assert not _problem_mentions_pregnancy_as_problem(str(p)), (
            f"sem32 v2 contiene anti-patrón: '{p}'"
        )
    text = " ".join(str(p).lower() for p in problems)
    assert "diabetes" in text, f"sem32 v2 perdió DG: {problems}"
    assert "macrosom" in text, f"sem32 v2 perdió macrosomía: {problems}"


def test_v2_sem38_no_pregnancy_in_active_problems(extracted_v2) -> None:
    """sem38: DG controlada con insulina + macrosomía + anemia preservados."""
    problems = extracted_v2[38].get("active_problems", []) or []
    for p in problems:
        assert not _problem_mentions_pregnancy_as_problem(str(p)), (
            f"sem38 v2 contiene anti-patrón: '{p}'"
        )
    text = " ".join(str(p).lower() for p in problems)
    assert "diabetes" in text, f"sem38 v2 perdió DG: {problems}"
    assert "macrosom" in text, f"sem38 v2 perdió macrosomía: {problems}"
    assert "anemia" in text, f"sem38 v2 perdió anemia: {problems}"


# =========================================================================
# No-regresión: campos estructurales preservados entre v1 y v2
# =========================================================================


def test_v2_preserves_gestational_age_weeks(extracted_v1, extracted_v2) -> None:
    """v2 sigue capturando EG correctamente (no depende de active_problems).

    Tolerancia: ±0.5 semanas — pequeñas diferencias en el cálculo
    decimal son aceptables; lo que importa es la magnitud.
    """
    for sem in (16, 24, 32, 38):
        ga_v1 = extracted_v1[sem].get("gestational_age_weeks")
        ga_v2 = extracted_v2[sem].get("gestational_age_weeks")
        assert ga_v2 is not None, f"sem{sem} v2 perdió gestational_age_weeks"
        assert abs(ga_v2 - ga_v1) <= 0.5, (
            f"sem{sem} EG cambió más allá de tolerancia: v1={ga_v1}, v2={ga_v2}"
        )


def test_v2_preserves_patient_age(extracted_v1, extracted_v2) -> None:
    """patient_age estable: la paciente es la misma en v1 y v2."""
    for sem in (16, 24, 32, 38):
        assert extracted_v1[sem].get("patient_age") == extracted_v2[sem].get(
            "patient_age"
        ), f"sem{sem} patient_age cambió entre v1 y v2"


def test_v2_preserves_fum_and_fpp(extracted_v1, extracted_v2) -> None:
    """FUM y FPP son fechas duras que no deben moverse entre prompts."""
    for sem in (16, 24, 32, 38):
        assert extracted_v1[sem].get("fum") == extracted_v2[sem].get("fum"), (
            f"sem{sem} FUM cambió: v1={extracted_v1[sem].get('fum')}, "
            f"v2={extracted_v2[sem].get('fum')}"
        )
        assert extracted_v1[sem].get("fpp") == extracted_v2[sem].get("fpp"), (
            f"sem{sem} FPP cambió: v1={extracted_v1[sem].get('fpp')}, "
            f"v2={extracted_v2[sem].get('fpp')}"
        )


def test_v2_preserves_confidence_score(extracted_v2) -> None:
    """v2 mantiene confidence_score alto (>=0.85) en los 4 casos."""
    for sem in (16, 24, 32, 38):
        score = extracted_v2[sem].get("confidence_score")
        assert score is not None, f"sem{sem} v2 sin confidence_score"
        assert score >= 0.85, (
            f"sem{sem} v2 confidence_score cayó por debajo de 0.85: {score}"
        )


def test_v2_preserves_lab_results_count(extracted_v1, extracted_v2) -> None:
    """v2 captura aproximadamente la misma cantidad de labs que v1.

    Tolerancia: ±1 lab. Cambios mayores indicarían regresión en otra
    parte del prompt (no es el objetivo de v2).
    """
    for sem in (16, 24, 32, 38):
        labs_v1 = len(extracted_v1[sem].get("lab_results", []) or [])
        labs_v2 = len(extracted_v2[sem].get("lab_results", []) or [])
        assert abs(labs_v1 - labs_v2) <= 1, (
            f"sem{sem} cuenta de lab_results cambió >1: v1={labs_v1}, v2={labs_v2}"
        )


def test_v2_risk_factors_non_empty(extracted_v2) -> None:
    """risk_factors no debe estar vacío en ningún caso longitudinal.

    Sanity: v2 puede mover items de active_problems a risk_factors
    (antecedentes familiares), pero no debe vaciar el campo. Si lo hace,
    es señal de regresión.
    """
    for sem in (16, 24, 32, 38):
        risk = extracted_v2[sem].get("risk_factors", []) or []
        assert risk, f"sem{sem} v2 risk_factors vacío — posible regresión"


def test_v2_notes_summary_non_empty(extracted_v2) -> None:
    """notes_summary preservado (campo crítico para handoff clínico)."""
    for sem in (16, 24, 32, 38):
        notes = extracted_v2[sem].get("notes_summary", "")
        assert notes and len(notes.strip()) >= 50, (
            f"sem{sem} v2 notes_summary vacío o muy corto: {notes[:80]!r}"
        )


# =========================================================================
# Continuidad clínica preservada (mirror laxo de test_longitudinal_continuity)
# =========================================================================


def test_v2_gestational_age_progresses_monotonically(extracted_v2) -> None:
    """v2 mantiene la progresión EG: sem16 < sem24 < sem32 < sem38."""
    egs = [extracted_v2[s].get("gestational_age_weeks") for s in (16, 24, 32, 38)]
    assert all(e is not None for e in egs), f"alguna EG falta: {egs}"
    for i in range(1, len(egs)):
        assert egs[i] > egs[i - 1], (
            f"v2 EG no crece monótonamente entre control {i - 1} y {i}: {egs}"
        )


def test_v2_diabetes_appears_at_week_24_and_later(extracted_v2) -> None:
    """Mirror del test de v1: DG debe aparecer como problema activo en
    sem24/32/38 (no antes)."""
    for sem in (24, 32, 38):
        problems = extracted_v2[sem].get("active_problems", []) or []
        text = " ".join(str(p).lower() for p in problems)
        assert "diabetes" in text, (
            f"v2 sem{sem} debe incluir diabetes en active_problems: {problems}"
        )
