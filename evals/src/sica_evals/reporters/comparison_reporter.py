"""Renderers para ``ComparisonResult``: consola, Markdown y JSON.

Cada renderer es puro: recibe un ``ComparisonResult`` y devuelve un string
(o lo escribe a path explícito). Sin side-effects ocultos.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from sica_evals.comparators.prompt_comparator import ComparisonResult

_VERDICT_EMOJI = {
    "GREEN": "OK",
    "YELLOW": "WARN",
    "RED": "FAIL",
}


def _format_overlap(value: float) -> str:
    """Formatea Jaccard como porcentaje con un decimal."""
    return f"{value * 100:.1f}%"


def _format_cost(value: float | None) -> str:
    return f"${value:.4f}" if value is not None else "n/d"


def _format_delta_cost(value: float | None) -> str:
    if value is None:
        return "n/d"
    sign = "+" if value >= 0 else ""
    return f"{sign}${value:.4f}"


def render_console(result: ComparisonResult) -> str:
    """Render para stdout — texto plano, sin colores (compat Windows cp1252)."""
    lines: list[str] = []
    sep = "=" * 64

    lines.append(sep)
    lines.append(
        f"COMPARACIÓN: {result.prompt_name} v{result.version_a} vs v{result.version_b}"
    )
    lines.append(sep)
    lines.append(f"Casos comparados: {result.n_cases}")
    if result.n_cases == 0:
        lines.append("")
        lines.append("ATENCIÓN: 0 casos comparados. Verifica fixtures_dir.")
        lines.append(sep)
        return "\n".join(lines)

    cases_with_regressions = sum(1 for m in result.case_metrics if m.regressions)
    cases_with_improvements = sum(1 for m in result.case_metrics if m.improvements)
    lines.append(
        f"Casos con regresiones: {cases_with_regressions} "
        f"({cases_with_regressions / result.n_cases:.0%})"
    )
    lines.append(
        f"Casos con mejoras:     {cases_with_improvements} "
        f"({cases_with_improvements / result.n_cases:.0%})"
    )
    lines.append("")
    lines.append(f"Veredicto: {result.verdict} [{_VERDICT_EMOJI[result.verdict]}]")
    lines.append(f"Razón:     {result.verdict_reason}")
    lines.append("")

    # Detalle por caso
    lines.append("-" * 64)
    lines.append("Detalle por caso:")
    lines.append("")
    for m in result.case_metrics:
        lines.append(f"  {m.case_id}:")
        identity_ok = all(
            [m.patient_age_match, m.gestational_age_match, m.fum_match, m.fpp_match]
        )
        if identity_ok:
            lines.append("    Identidad (edad, GA, FUM, FPP): match")
        else:
            mismatches = []
            if not m.patient_age_match:
                mismatches.append("edad")
            if not m.gestational_age_match:
                mismatches.append("GA")
            if not m.fum_match:
                mismatches.append("FUM")
            if not m.fpp_match:
                mismatches.append("FPP")
            lines.append(f"    Identidad: DIVERGE en {', '.join(mismatches)}")

        lines.append(
            f"    active_problems: {len(m.active_problems_v1)} -> {len(m.active_problems_v2)} "
            f"(overlap {_format_overlap(m.active_problems_overlap)})"
        )
        if m.active_problems_added:
            lines.append(f"      + agregado: {m.active_problems_added}")
        if m.active_problems_removed:
            lines.append(f"      - removido: {m.active_problems_removed}")

        lines.append(
            f"    risk_factors:    {len(m.risk_factors_v1)} -> {len(m.risk_factors_v2)} "
            f"(overlap {_format_overlap(m.risk_factors_overlap)})"
        )
        lines.append(
            f"    confidence:      {m.confidence_score_v1:.2f} -> "
            f"{m.confidence_score_v2:.2f} (Δ {m.confidence_delta:+.2f})"
        )
        lines.append(
            f"    evidence_spans:  {m.evidence_spans_count_v1} -> {m.evidence_spans_count_v2}"
        )
        lines.append(
            f"    lab_results:     {m.lab_results_count_v1} -> {m.lab_results_count_v2}"
        )
        lines.append(
            f"    notes_keywords:  overlap {_format_overlap(m.notes_summary_keyword_overlap)}"
        )
        if m.regressions:
            lines.append(f"    REGRESIONES: {m.regressions}")
        if m.improvements:
            lines.append(f"    Mejoras:     {m.improvements}")
        if m.neutral_changes:
            lines.append(f"    Neutrales:   {m.neutral_changes}")
        lines.append("")

    lines.append("-" * 64)
    lines.append("Costos totales:")
    lines.append(f"  v{result.version_a}: {_format_cost(result.total_cost_v1_usd)}")
    lines.append(
        f"  v{result.version_b}: {_format_cost(result.total_cost_v2_usd)} "
        f"(Δ {_format_delta_cost(result.total_cost_delta_usd)})"
    )
    lines.append(sep)
    return "\n".join(lines)


def render_markdown(result: ComparisonResult) -> str:
    """Render como reporte Markdown (humano-legible, side-by-side por caso)."""
    lines: list[str] = []
    lines.append(
        f"# Comparación `{result.prompt_name}`: v{result.version_a} vs v{result.version_b}"
    )
    lines.append("")
    lines.append(f"**Veredicto:** `{result.verdict}` — {result.verdict_reason}")
    lines.append("")
    lines.append(f"- Casos comparados: **{result.n_cases}**")
    if result.n_cases > 0:
        cwr = sum(1 for m in result.case_metrics if m.regressions)
        cwi = sum(1 for m in result.case_metrics if m.improvements)
        lines.append(f"- Casos con regresiones: **{cwr}** ({cwr / result.n_cases:.0%})")
        lines.append(f"- Casos con mejoras: **{cwi}** ({cwi / result.n_cases:.0%})")
    lines.append(f"- Costo total v{result.version_a}: {_format_cost(result.total_cost_v1_usd)}")
    lines.append(
        f"- Costo total v{result.version_b}: {_format_cost(result.total_cost_v2_usd)} "
        f"(Δ {_format_delta_cost(result.total_cost_delta_usd)})"
    )
    lines.append("")

    # Tabla resumen por caso
    lines.append("## Resumen por caso")
    lines.append("")
    lines.append(
        "| Caso | Identidad | active_problems | risk_factors | confidence Δ | evidence | regresiones |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for m in result.case_metrics:
        identity_ok = all(
            [m.patient_age_match, m.gestational_age_match, m.fum_match, m.fpp_match]
        )
        identity_cell = "match" if identity_ok else "DIVERGE"
        ap_cell = (
            f"{len(m.active_problems_v1)}→{len(m.active_problems_v2)} "
            f"({_format_overlap(m.active_problems_overlap)})"
        )
        rf_cell = (
            f"{len(m.risk_factors_v1)}→{len(m.risk_factors_v2)} "
            f"({_format_overlap(m.risk_factors_overlap)})"
        )
        conf_cell = f"{m.confidence_delta:+.2f}"
        ev_cell = f"{m.evidence_spans_count_v1}→{m.evidence_spans_count_v2}"
        reg_cell = ", ".join(m.regressions) if m.regressions else "—"
        lines.append(
            f"| {m.case_id} | {identity_cell} | {ap_cell} | {rf_cell} | "
            f"{conf_cell} | {ev_cell} | {reg_cell} |"
        )
    lines.append("")

    # Detalle por caso
    lines.append("## Detalle por caso")
    lines.append("")
    for m in result.case_metrics:
        lines.append(f"### `{m.case_id}`")
        lines.append("")
        if m.active_problems_added:
            lines.append("**Agregados a active_problems en v2:**")
            for item in m.active_problems_added:
                lines.append(f"- `{item}`")
            lines.append("")
        if m.active_problems_removed:
            lines.append("**Removidos de active_problems en v2:**")
            for item in m.active_problems_removed:
                lines.append(f"- `{item}`")
            lines.append("")
        if m.regressions:
            lines.append(f"**Regresiones detectadas:** {', '.join(f'`{r}`' for r in m.regressions)}")
            lines.append("")
        if m.improvements:
            lines.append(f"**Mejoras detectadas:** {', '.join(f'`{r}`' for r in m.improvements)}")
            lines.append("")
        if m.neutral_changes:
            lines.append(
                f"**Cambios neutrales:** {', '.join(f'`{r}`' for r in m.neutral_changes)}"
            )
            lines.append("")
        lines.append(
            f"- notes_summary keyword overlap: **{_format_overlap(m.notes_summary_keyword_overlap)}**"
        )
        lines.append(
            f"- notes_summary length: {m.notes_summary_length_v1} → {m.notes_summary_length_v2} chars"
        )
        lines.append("")
    return "\n".join(lines)


def render_json(result: ComparisonResult) -> str:
    """Render como JSON estructurado (machine-readable)."""
    payload = {
        "prompt_name": result.prompt_name,
        "version_a": result.version_a,
        "version_b": result.version_b,
        "n_cases": result.n_cases,
        "verdict": result.verdict,
        "verdict_reason": result.verdict_reason,
        "totals": {
            "regressions": result.total_regressions,
            "improvements": result.total_improvements,
            "neutral_changes": result.total_neutral,
            "cost_v1_usd": result.total_cost_v1_usd,
            "cost_v2_usd": result.total_cost_v2_usd,
            "cost_delta_usd": result.total_cost_delta_usd,
        },
        "cases": [asdict(m) for m in result.case_metrics],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def write_reports(result: ComparisonResult, output_dir: Path, basename: str) -> dict[str, Path]:
    """Escribe los 3 formatos a disco. Devuelve mapping format → path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    md_path = output_dir / f"{basename}.md"
    md_path.write_text(render_markdown(result), encoding="utf-8")
    written["markdown"] = md_path
    json_path = output_dir / f"{basename}.json"
    json_path.write_text(render_json(result), encoding="utf-8")
    written["json"] = json_path
    return written
