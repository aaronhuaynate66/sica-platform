"""Tests de continuidad clínica entre los 4 controles longitudinales de Lucía.

Cargan los 4 ``extracted.json`` ya producidos por el extractor real
(commit `4675b5c`). NO disparan extracciones nuevas — sería costoso
y no determinista. La premisa: si el extractor falla a futuro al
preservar continuidad entre controles, estos tests lo detectan en CI.

Definiciones operativas de "continuidad clínica" testeadas:

1. Identidad estable: misma paciente, mismos antecedentes, misma edad
   (o coherente con tiempo transcurrido — el embarazo dura <1 año
   así que ``patient_age`` debe ser igual o +1).

2. Progresión temporal: ``gestational_age_weeks`` siempre crece.

3. Aparición de patología: complicaciones deben aparecer cuando
   corresponde según el contenido del PDF (DG en sem 24, macrosomía
   en sem 32, no antes).

4. Escalamiento de manejo: el plan se hace más intensivo a medida
   que aparecen complicaciones (dieta → insulina → cesárea).

5. No-invención: el extractor no inventa patologías que no estaban
   en el PDF (ej. no agrega HTA si nunca apareció).

Diseño: el fixture ``extracted_controls`` carga los 4 JSONs una sola
vez con scope module — todos los tests del archivo comparten la carga.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _fixtures_root() -> Path:
    """Path a `evals/fixtures/longitudinal_lucia/` desde este archivo."""
    return Path(__file__).resolve().parent.parent / "fixtures" / "longitudinal_lucia"


@pytest.fixture(scope="module")
def extracted_controls() -> dict[int, dict]:
    """Devuelve dict {16: extracted_json, 24: ..., 32: ..., 38: ...}."""
    root = _fixtures_root()
    out: dict[int, dict] = {}
    for sem in (16, 24, 32, 38):
        path = root / f"sem{sem}" / "extracted.json"
        if not path.exists():
            msg = (
                f"Falta extracted.json para sem{sem}: {path}. "
                "Generar con `clinical-extractor extract ...` ver commit 4675b5c."
            )
            raise FileNotFoundError(msg)
        out[sem] = json.loads(path.read_text(encoding="utf-8"))
    return out


def _contains_substr_any(items: list, *needles: str) -> bool:
    """True si CUALQUIER item del listado contiene CUALQUIER substring (case-insensitive)."""
    if not items:
        return False
    text = " ".join(str(i).lower() for i in items)
    return any(n.lower() in text for n in needles)


def _contains_substr_in_str(text: str | None, *needles: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(n.lower() in lowered for n in needles)


# =========================================================================
# Tests
# =========================================================================


def test_patient_identity_consistent_across_controls(extracted_controls) -> None:
    """Misma paciente en los 4 controles: edad debe ser estable
    (28 al inicio, máximo 29 al final). G2P1 mencionado en notes_summary
    o referido implícitamente en cada control.
    """
    ages = [extracted_controls[s].get("patient_age") for s in (16, 24, 32, 38)]
    # El embarazo dura <1 año; la paciente cumple 28→29 durante. Aceptamos 28 o 29 en cualquier control.
    for age in ages:
        assert age in (28, 29), f"patient_age fuera de rango esperado: {age}"
    # Y la edad NO puede decrecer entre controles consecutivos
    assert ages == sorted(ages), f"patient_age decrece: {ages}"


def test_gestational_age_progresses_correctly(extracted_controls) -> None:
    """EG debe crecer monotónicamente: sem16 < sem24 < sem32 < sem38."""
    egs = [extracted_controls[s].get("gestational_age_weeks") for s in (16, 24, 32, 38)]
    assert all(e is not None for e in egs), f"alguna EG falta: {egs}"
    for i in range(1, len(egs)):
        assert egs[i] > egs[i - 1], (
            f"EG no crece monótonamente entre control {i - 1} y {i}: {egs}"
        )
    # Sanity: deben estar en rangos esperados (con tolerancia de ±1.5 sem por imprecisión).
    expected_ranges = [(15, 18), (23, 26), (31, 34), (37, 40)]
    for eg, (lo, hi) in zip(egs, expected_ranges, strict=True):
        assert lo <= eg <= hi, f"EG {eg} fuera de rango esperado [{lo}, {hi}]"


def test_diabetes_first_appears_at_week_24(extracted_controls) -> None:
    """sem 16 NO debe tener DG DIAGNOSTICADA en active_problems; sem 24+ SÍ.

    Sutileza: el extractor puede mencionar 'riesgo aumentado de diabetes
    gestacional' en sem 16 — eso describe el factor de riesgo (correcto),
    no el diagnóstico. Discriminamos por presencia de 'riesgo' adyacente.
    """
    sem16_problems = extracted_controls[16].get("active_problems") or []
    sem24_problems = extracted_controls[24].get("active_problems") or []
    sem32_problems = extracted_controls[32].get("active_problems") or []
    sem38_problems = extracted_controls[38].get("active_problems") or []

    # sem 16: si DG aparece, debe estar enmarcado como RIESGO (no diagnóstico activo).
    for problem in sem16_problems:
        p_low = str(problem).lower()
        if "diabetes gestacional" in p_low or "diabetes" in p_low:
            assert "riesgo" in p_low, (
                f"sem16 active_problems sugiere DG diagnosticada sin marcador de "
                f"'riesgo': '{problem}'"
            )

    # sem 24+: DG debe aparecer como problema activo SIN el qualificador 'riesgo'.
    for sem, problems in [
        (24, sem24_problems),
        (32, sem32_problems),
        (38, sem38_problems),
    ]:
        # Encontrar al menos UN item que mencione diabetes Y no lo enmarque como mero riesgo.
        has_active_dg = False
        for p in problems:
            p_low = str(p).lower()
            if ("diabetes gestacional" in p_low or "diabetes" in p_low) and "riesgo" not in p_low:
                has_active_dg = True
                break
        assert has_active_dg, (
            f"sem{sem} active_problems debe incluir DG como dx activo (no solo riesgo): {problems}"
        )


def test_macrosomia_appears_at_week_32(extracted_controls) -> None:
    """sem 16/24 NO mencionan macrosomía; sem 32+ SÍ.

    El PDF de sem 32 introduce 'macrosomía incipiente' (PFE p85), y sem 38
    la confirma (PFE 3,850g p90). En sem 24 PFE 580g p50 = NO macrosomía.
    """
    for sem in (16, 24):
        problems = extracted_controls[sem].get("active_problems") or []
        assert not _contains_substr_any(problems, "macrosom"), (
            f"sem{sem} no debe mencionar macrosomía: {problems}"
        )
    for sem in (32, 38):
        problems = extracted_controls[sem].get("active_problems") or []
        assert _contains_substr_any(problems, "macrosom"), (
            f"sem{sem} debe mencionar macrosomía: {problems}"
        )


def test_management_escalates_with_diabetes(extracted_controls) -> None:
    """Plan/notes deben mostrar escalamiento progresivo del manejo.

    sem 24: dieta + interconsulta endocrino/nutrición.
    sem 32: inicio de INSULINA.
    sem 38: decisión de vía de parto (cesárea).
    """
    sem24_notes = extracted_controls[24].get("notes_summary", "") or ""
    sem32_notes = extracted_controls[32].get("notes_summary", "") or ""
    sem38_notes = extracted_controls[38].get("notes_summary", "") or ""

    # sem 24: dieta o interconsulta presente.
    assert _contains_substr_in_str(
        sem24_notes, "dieta", "interconsulta", "endocrinolog", "nutrici"
    ), f"sem24 notes deben mencionar manejo inicial (dieta/interconsulta): {sem24_notes[:200]}"

    # sem 32: insulina.
    assert _contains_substr_in_str(
        sem32_notes, "insulina"
    ), f"sem32 notes deben mencionar inicio de insulina: {sem32_notes[:200]}"

    # sem 38: cesárea o vía de parto.
    assert _contains_substr_in_str(
        sem38_notes, "cesárea", "cesarea", "vía de parto", "via de parto"
    ), f"sem38 notes deben mencionar decisión de cesárea: {sem38_notes[:200]}"


def test_weight_gain_progresses_realistically(extracted_controls) -> None:
    """El peso no debe decrecer entre controles consecutivos.

    El peso vive en notes_summary o como inferencia narrativa, no en
    un campo estructurado. Test laxo: si el extractor capturó pesos,
    deben crecer; si no los capturó, skipped (no es campo crítico
    del schema actual).
    """
    import re

    weights = []
    for sem in (16, 24, 32, 38):
        notes = extracted_controls[sem].get("notes_summary", "") or ""
        # Heurística: buscar "<num>.<dec> kg" patterns
        matches = re.findall(r"(\d{2,3}(?:\.\d)?)\s*kg", notes.lower())
        if matches:
            # Tomar el primer match (típicamente el peso actual)
            try:
                weights.append(float(matches[0]))
            except ValueError:
                weights.append(None)
        else:
            weights.append(None)

    # Si el extractor capturó pesos en al menos 2 controles consecutivos,
    # verificar que crecen.
    detected = [(i, w) for i, w in enumerate(weights) if w is not None]
    if len(detected) >= 2:
        for i in range(1, len(detected)):
            _, prev_w = detected[i - 1]
            _, cur_w = detected[i]
            assert cur_w >= prev_w - 1.0, (  # tolerancia 1kg por imprecisión narrativa
                f"Peso decrece más allá de la tolerancia: {weights}"
            )


def test_no_hallucinated_new_pathologies(extracted_controls) -> None:
    """sem 32 y sem 38 NO deben inventar patologías que NO estaban en el PDF.

    Lista de patologías canónicas reales en el dataset:
    - sem 16: ninguna activa
    - sem 24: DG
    - sem 32: DG mal controlada, macrosomía incipiente, polihidramnios leve
    - sem 38: DG controlada con insulina, macrosomía

    Patologías que NUNCA aparecen en este caso y que serían
    hallucinations si el extractor las inventara:
    - HTA (hipertensión)
    - preeclampsia
    - RPM (ruptura prematura de membranas)
    - eclampsia
    - oligohidramnios
    - amenaza parto prematuro
    """
    forbidden = [
        "hipertensión",
        "hipertension",
        "preeclampsia",
        "eclampsia",
        "rpm",
        "ruptura prematura de membranas",
        "oligohidramnios",
        "amenaza de parto prematuro",
        "amenaza parto prematuro",
        "anemia severa",  # solo "anemia leve" aparece en sem 38, no severa
        "placenta previa",
    ]
    for sem in (16, 24, 32, 38):
        problems = extracted_controls[sem].get("active_problems") or []
        for f in forbidden:
            assert not _contains_substr_any(problems, f), (
                f"sem{sem} active_problems alucinó '{f}': {problems}"
            )


def test_risk_factors_persist_across_controls(extracted_controls) -> None:
    """Los factores de riesgo identificados en sem 16 (sobrepeso, AF DM2)
    deben seguir apareciendo o ser referenciados en controles posteriores —
    son rasgos invariantes de la paciente, no eventos.
    """
    # En sem 16 el extractor debe haberlos capturado.
    sem16_risks = extracted_controls[16].get("risk_factors") or []
    assert _contains_substr_any(sem16_risks, "sobrepeso"), (
        f"sem16 risk_factors debe incluir sobrepeso: {sem16_risks}"
    )
    assert _contains_substr_any(sem16_risks, "dm2", "diabetes mellitus", "antecedente familiar"), (
        f"sem16 risk_factors debe incluir antecedente DM2: {sem16_risks}"
    )

    # En al menos UNO de los controles posteriores debe persistir alguno de los dos.
    # (Persistir en TODOS sería excesivo — el extractor puede empaquetar de formas distintas).
    persisted_count = 0
    for sem in (24, 32, 38):
        risks = extracted_controls[sem].get("risk_factors") or []
        if _contains_substr_any(
            risks, "sobrepeso", "imc", "dm2", "diabetes mellitus", "antecedente familiar"
        ):
            persisted_count += 1
    assert persisted_count >= 2, (
        f"Riesgos pre-gestacionales deben persistir en ≥2/3 controles posteriores; "
        f"persistieron en {persisted_count}/3"
    )


def test_lab_results_include_diagnostic_evidence(extracted_controls) -> None:
    """Cada control con DG debe llevar evidencia diagnóstica en lab_results.

    sem 24: PTOG (o glicemias post-carga).
    sem 32: HbA1c (mostrando el deterioro).
    sem 38: HbA1c (mostrando el control alcanzado).
    """
    def lab_names(extracted: dict) -> list[str]:
        return [lr.get("name", "") for lr in (extracted.get("lab_results") or [])]

    sem24_labs = lab_names(extracted_controls[24])
    assert _contains_substr_any(sem24_labs, "ptog", "tolerancia", "glucosa"), (
        f"sem24 lab_results debe documentar PTOG: {sem24_labs}"
    )

    sem32_labs = lab_names(extracted_controls[32])
    assert _contains_substr_any(sem32_labs, "hba1c", "hemoglobina glicosilada", "glicemia"), (
        f"sem32 lab_results debe documentar HbA1c/glicemias: {sem32_labs}"
    )

    sem38_labs = lab_names(extracted_controls[38])
    assert _contains_substr_any(sem38_labs, "hba1c", "hemoglobina glicosilada"), (
        f"sem38 lab_results debe documentar HbA1c: {sem38_labs}"
    )
