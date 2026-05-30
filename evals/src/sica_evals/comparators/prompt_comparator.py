"""Comparator de prompts: ejecuta o lee 2 versiones sobre un dataset y agrega métricas.

Caso de uso primario:
    Validar que ``extract_obstetric_v(N+1)`` NO regresiona métricas clínicas
    vs. ``extract_obstetric_vN`` antes de promover la nueva versión en
    ``DEFAULT_VERSIONS``. Habilita decisiones informadas, evita drift silencioso
    al subir el pin del default.

Modos:
    - **cached**: cero costo Anthropic. Lee JSONs ya extraídos en fixtures
      (``extracted.json`` para vN, ``extracted_v(N+1).json`` para vN+1).
      Útil para iterar localmente y bloquear regresiones obvias.
    - **fresh**: corre el extractor real contra Anthropic para ambas versiones
      sobre los PDFs de la carpeta provista. Costo aproximado: USD 0.04 por
      PDF por versión. Genera fixtures y luego invoca el flujo cached.

Veredicto agregado (semáforo):
    - GREEN  → ≥50% mejoras, 0% regresiones.
    - YELLOW → regresiones >0% y <25%, o cambios mayoritariamente neutrales.
    - RED    → regresiones ≥25% de casos.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from sica_evals.comparators.prompt_metrics import (
    ComparisonMetrics,
    compare_outputs,
)

logger = logging.getLogger("sica_evals.comparators.prompt_comparator")

Verdict = Literal["GREEN", "YELLOW", "RED"]


@dataclass(frozen=True)
class ComparisonResult:
    """Resultado agregado de la comparación sobre todo el dataset."""

    prompt_name: str
    version_a: int
    version_b: int
    n_cases: int
    case_metrics: list[ComparisonMetrics]

    # Agregados (suma de eventos a través de casos)
    total_regressions: int
    total_improvements: int
    total_neutral: int

    # Veredicto operacional
    verdict: Verdict
    verdict_reason: str

    # Costos agregados (None si no había metadata en ningún caso)
    total_cost_v1_usd: float
    total_cost_v2_usd: float
    total_cost_delta_usd: float


def compute_verdict(case_metrics: list[ComparisonMetrics]) -> tuple[Verdict, str]:
    """Decide el semáforo agregado a partir de las métricas por caso.

    Lógica:
        - 0 casos → RED (no se pudo comparar nada).
        - Cualquier caso con ``patient_age``/``fum``/``fpp`` o pérdida de
          GA → RED inmediato. Estos son contratos de identidad/cronología
          que NO pueden regresionar bajo ningún criterio.
        - ≥25% casos con regresiones → RED.
        - 10-25% casos con regresiones → YELLOW.
        - <10% regresiones y ≥50% improvements → GREEN.
        - Resto → YELLOW (cambios mayoritariamente neutrales).
    """
    n = len(case_metrics)
    if n == 0:
        return "RED", "Sin casos comparados (dataset vacío o fixtures faltantes)"

    # Hard-fail: si algún caso pierde identidad cronológica/numérica básica,
    # es regresión inaceptable independiente de los demás.
    critical_regression_fields = {"patient_age", "fum", "fpp", "gestational_age_weeks"}
    for m in case_metrics:
        critical_hit = critical_regression_fields & set(m.regressions)
        if critical_hit:
            return (
                "RED",
                f"Caso {m.case_id!r} regresiona campos críticos: {sorted(critical_hit)}",
            )

    cases_with_regressions = sum(1 for m in case_metrics if m.regressions)
    cases_with_improvements = sum(1 for m in case_metrics if m.improvements)

    regression_rate = cases_with_regressions / n
    improvement_rate = cases_with_improvements / n

    if regression_rate >= 0.25:
        return (
            "RED",
            f"{regression_rate:.0%} de casos con regresión (umbral 25%)",
        )
    if regression_rate >= 0.10:
        return (
            "YELLOW",
            f"{regression_rate:.0%} de casos con regresión (>0%, <25%)",
        )
    if improvement_rate >= 0.50:
        return (
            "GREEN",
            f"{improvement_rate:.0%} de casos con mejoras, 0% regresiones",
        )
    return (
        "YELLOW",
        f"{improvement_rate:.0%} mejoras, {regression_rate:.0%} regresiones — mayoría neutral",
    )


def _load_json(path: Path) -> dict[str, Any]:
    """Lee y parsea un JSON UTF-8."""
    data: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        msg = f"Esperaba dict en {path}, obtuvo {type(data).__name__}"
        raise ValueError(msg)
    return data


def compare_prompts_from_cached(
    prompt_name: str,
    version_a: int,
    version_b: int,
    fixtures_dir: Path,
    fixture_pattern_a: str = "extracted.json",
    fixture_pattern_b: str = "extracted_v2.json",
    meta_filename: str = "meta.json",
) -> ComparisonResult:
    """Compara 2 versiones usando JSONs ya extraídos en ``fixtures_dir``.

    Estructura esperada::

        fixtures_dir/
            case_a/
                extracted.json       # output v_a
                extracted_v2.json    # output v_b
                meta.json            # opcional, con cost_usd/latency_ms
            case_b/...

    Args:
        prompt_name: Nombre lógico del prompt (e.g. ``"extract_obstetric"``).
        version_a, version_b: Números de versión a etiquetar en el reporte.
        fixtures_dir: Carpeta raíz con subdirectorios por caso.
        fixture_pattern_a, fixture_pattern_b: Nombre del archivo dentro de
            cada caso con el output. Default: ``extracted.json`` para v1,
            ``extracted_v2.json`` para v2.
        meta_filename: Archivo opcional con metadata operacional por caso.

    Returns:
        ``ComparisonResult`` agregado. Si un caso no tiene los dos archivos
        de extracción, se skip-ea con log INFO (no se cuenta).
    """
    case_metrics: list[ComparisonMetrics] = []

    if not fixtures_dir.exists():
        msg = f"fixtures_dir no existe: {fixtures_dir}"
        raise FileNotFoundError(msg)

    for case_dir in sorted(fixtures_dir.iterdir()):
        if not case_dir.is_dir():
            continue

        path_a = case_dir / fixture_pattern_a
        path_b = case_dir / fixture_pattern_b
        if not (path_a.exists() and path_b.exists()):
            logger.info(
                "Skip caso %s: faltan fixtures (%s=%s, %s=%s)",
                case_dir.name,
                fixture_pattern_a,
                path_a.exists(),
                fixture_pattern_b,
                path_b.exists(),
            )
            continue

        output_a = _load_json(path_a)
        output_b = _load_json(path_b)

        meta_path = case_dir / meta_filename
        meta_a: dict[str, Any] | None = None
        meta_b: dict[str, Any] | None = None
        if meta_path.exists():
            # En modo cached el meta es per-caso, no per-versión. Lo
            # usamos como aproximación para ambos lados.
            meta_a = _load_json(meta_path)
            meta_b = meta_a

        m = compare_outputs(case_dir.name, output_a, output_b, meta_a, meta_b)
        case_metrics.append(m)

    verdict, reason = compute_verdict(case_metrics)

    total_cost_a = sum((m.cost_v1_usd or 0.0) for m in case_metrics)
    total_cost_b = sum((m.cost_v2_usd or 0.0) for m in case_metrics)

    return ComparisonResult(
        prompt_name=prompt_name,
        version_a=version_a,
        version_b=version_b,
        n_cases=len(case_metrics),
        case_metrics=case_metrics,
        total_regressions=sum(len(m.regressions) for m in case_metrics),
        total_improvements=sum(len(m.improvements) for m in case_metrics),
        total_neutral=sum(len(m.neutral_changes) for m in case_metrics),
        verdict=verdict,
        verdict_reason=reason,
        total_cost_v1_usd=total_cost_a,
        total_cost_v2_usd=total_cost_b,
        total_cost_delta_usd=total_cost_b - total_cost_a,
    )


def compare_prompts_fresh(
    prompt_name: str,
    version_a: int,
    version_b: int,
    pdfs_dir: Path,
    output_dir: Path,
) -> ComparisonResult:
    """Compara 2 versiones ejecutando extracción real contra Anthropic.

    Costo: ~USD 0.04 por PDF x 2 versiones x N PDFs. Genera los fixtures en
    ``output_dir/{case_name}/extracted_v{N}.json`` + ``meta.json`` y luego
    delega en :func:`compare_prompts_from_cached`.

    Requiere ``clinical_extractor`` importable y ``ANTHROPIC_API_KEY`` en env.
    """
    # Import diferido para no forzar la dependencia en modo cached.
    from clinical_extractor.extractor import extract_from_pdf

    if not pdfs_dir.exists():
        msg = f"pdfs_dir no existe: {pdfs_dir}"
        raise FileNotFoundError(msg)
    output_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(pdfs_dir.glob("*.pdf"))
    if not pdfs:
        msg = f"No se encontraron PDFs en {pdfs_dir}"
        raise FileNotFoundError(msg)

    file_a = f"extracted_v{version_a}.json"
    file_b = f"extracted_v{version_b}.json"
    meta_a_file = f"meta_v{version_a}.json"
    meta_b_file = f"meta_v{version_b}.json"

    for pdf_path in pdfs:
        case_name = pdf_path.stem
        case_dir = output_dir / case_name
        case_dir.mkdir(exist_ok=True)

        for version, out_file, meta_file in (
            (version_a, file_a, meta_a_file),
            (version_b, file_b, meta_b_file),
        ):
            logger.info("Extrayendo %s con %s_v%d", pdf_path.name, prompt_name, version)
            metadata_out: dict[str, Any] = {}
            summary = extract_from_pdf(
                pdf_path,
                prompt_version=version,
                metadata_out=metadata_out,
            )
            (case_dir / out_file).write_text(
                json.dumps(summary.model_dump(mode="json"), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            (case_dir / meta_file).write_text(
                json.dumps(metadata_out, indent=2, default=str, ensure_ascii=False),
                encoding="utf-8",
            )

    # En modo fresh tenemos metadata por versión: cargar y comparar con loop
    # explícito (no usamos compare_prompts_from_cached directamente porque
    # esa función comparte meta entre versiones).
    case_metrics: list[ComparisonMetrics] = []
    for case_dir in sorted(output_dir.iterdir()):
        if not case_dir.is_dir():
            continue
        path_a = case_dir / file_a
        path_b = case_dir / file_b
        if not (path_a.exists() and path_b.exists()):
            continue
        output_a = _load_json(path_a)
        output_b = _load_json(path_b)
        meta_a = _load_json(case_dir / meta_a_file) if (case_dir / meta_a_file).exists() else None
        meta_b = _load_json(case_dir / meta_b_file) if (case_dir / meta_b_file).exists() else None
        case_metrics.append(compare_outputs(case_dir.name, output_a, output_b, meta_a, meta_b))

    verdict, reason = compute_verdict(case_metrics)
    total_cost_a = sum((m.cost_v1_usd or 0.0) for m in case_metrics)
    total_cost_b = sum((m.cost_v2_usd or 0.0) for m in case_metrics)

    return ComparisonResult(
        prompt_name=prompt_name,
        version_a=version_a,
        version_b=version_b,
        n_cases=len(case_metrics),
        case_metrics=case_metrics,
        total_regressions=sum(len(m.regressions) for m in case_metrics),
        total_improvements=sum(len(m.improvements) for m in case_metrics),
        total_neutral=sum(len(m.neutral_changes) for m in case_metrics),
        verdict=verdict,
        verdict_reason=reason,
        total_cost_v1_usd=total_cost_a,
        total_cost_v2_usd=total_cost_b,
        total_cost_delta_usd=total_cost_b - total_cost_a,
    )
