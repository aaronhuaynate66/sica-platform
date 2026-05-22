"""Markdown report.

Output sections:
  1. Executive summary (cases passed gate)
  2. Aggregate metrics table
  3. Per-case results
  4. Critical findings (omissions + hallucinations)
  5. Run metadata
"""

from __future__ import annotations

from tabulate import tabulate

from sica_evals.schemas import HarnessReport

# Gate thresholds derived from ADR 0004 Nivel 2 + STRATEGY § 7.
FACTUAL_ACCURACY_GATE = 0.85
CRITICAL_OMISSIONS_GATE = 5  # absolute count per run; STRATEGY § 7 uses ≤5%


def _passes_gate(report: HarnessReport) -> bool:
    """Aggregate gate evaluation. R0 target: ≥0.85 factual accuracy mean."""
    return (
        report.aggregate_metrics.get("factual_accuracy_mean", 0.0) >= FACTUAL_ACCURACY_GATE
        and report.aggregate_metrics.get("critical_omissions_total", 0.0)
        <= CRITICAL_OMISSIONS_GATE
    )


def render_markdown(report: HarnessReport) -> str:
    """Build the report as a Markdown string."""
    lines: list[str] = []
    lines.append(f"# Reporte de evaluación — run `{report.run_id[:8]}`")
    lines.append("")
    lines.append(f"**Timestamp:** {report.timestamp.isoformat()}  ")
    lines.append(f"**Casos totales:** {report.cases_total}  ")
    lines.append(f"**Exitosos:** {report.cases_succeeded}  ")
    lines.append(f"**Fallidos:** {report.cases_failed}  ")
    lines.append(
        f"**Estado del gate R0:** {'✅ PASS' if _passes_gate(report) else '⚠️ FAIL'}"
    )
    lines.append("")

    # Aggregate
    lines.append("## Métricas agregadas")
    lines.append("")
    agg_rows = [[k, f"{v:.4f}" if isinstance(v, float) else v]
                for k, v in sorted(report.aggregate_metrics.items())]
    lines.append(tabulate(agg_rows, headers=["Métrica", "Valor"], tablefmt="github"))
    lines.append("")

    # Per-case results
    lines.append("## Resultados por caso")
    lines.append("")
    rows = []
    for r in report.per_case_results:
        rows.append(
            [
                r.case_id,
                f"{r.factual_accuracy:.4f}",
                r.critical_omissions,
                r.hallucinations,
                f"{r.confidence_calibration_error:.4f}",
                f"{r.latency_seconds:.2f}s",
                "❌ error" if r.error else "✅ ok",
            ]
        )
    lines.append(
        tabulate(
            rows,
            headers=[
                "case_id",
                "factual_accuracy",
                "critical_omissions",
                "hallucinations",
                "calib_error",
                "latency",
                "estado",
            ],
            tablefmt="github",
        )
    )
    lines.append("")

    # Critical findings
    lines.append("## Hallazgos críticos")
    lines.append("")
    any_findings = False
    for r in report.per_case_results:
        if r.error:
            any_findings = True
            lines.append(f"### {r.case_id} — error de ejecución")
            lines.append(f"- {r.error}")
            lines.append("")
            continue
        if r.critical_omissions == 0 and r.hallucinations == 0:
            continue
        any_findings = True
        lines.append(f"### {r.case_id}")
        if r.critical_omissions > 0:
            lines.append(f"- ⚠️ {r.critical_omissions} omisión(es) crítica(s):")
            for fc in r.field_comparisons:
                if fc.weight >= 2.0 and fc.match_type == "missing":
                    lines.append(
                        f"  - `{fc.field_name}` — esperado: `{fc.expected_value!r}`"
                    )
        if r.hallucinations > 0:
            lines.append(f"- 🚨 {r.hallucinations} alucinación(es):")
            for desc in r.hallucination_descriptions:
                lines.append(f"  - {desc}")
        lines.append("")
    if not any_findings:
        lines.append("_(ningún hallazgo crítico — todos los casos limpios)_")
        lines.append("")

    # Metadata
    lines.append("## Metadatos del run")
    lines.append("")
    meta_rows = [[k, str(v)] for k, v in sorted(report.metadata.items())]
    lines.append(tabulate(meta_rows, headers=["Clave", "Valor"], tablefmt="github"))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("_Generado por sica-evals harness._")
    lines.append("")

    return "\n".join(lines)
