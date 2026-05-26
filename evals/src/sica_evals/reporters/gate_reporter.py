"""Reportero del harness gate — formato pensado para PR comments.

A diferencia de ``markdown_reporter.render_markdown``, que reporta un run
aislado, este reporter compara un ``HarnessReport`` actual contra un
baseline y formatea el ``GateResult`` con tabla de deltas, lista de
violaciones, y guía de próximos pasos.
"""

from __future__ import annotations

from typing import Any

from tabulate import tabulate

from sica_evals.comparators.gate_comparator import GateResult
from sica_evals.schemas import HarnessReport


def _fmt(value: float | None, ndigits: int = 4) -> str:
    if value is None:
        return "—"
    if value != value:  # NaN
        return "—"
    return f"{value:.{ndigits}f}"


def _metric_label(name: str) -> str:
    return {
        "factual_accuracy": "Factual Accuracy",
        "critical_omissions": "Critical Omissions",
        "hallucination_count": "Hallucinations",
        "hallucinations": "Hallucinations",
        "ece": "ECE (Calibration)",
        "calibration_error": "ECE (Calibration)",
        "latency_seconds": "Latency (s)",
    }.get(name, name)


def _threshold_label(rule: dict[str, Any], ttype: str) -> str:
    if ttype == "relative_decline":
        return f"max -{rule.get('max_decline_pp', 0)}"
    if ttype == "absolute_max":
        return f"max {rule.get('max_value', 0)}"
    if ttype == "absolute_min":
        return f"min {rule.get('min_value', 0)}"
    return "—"


def render_gate_report(
    actual: HarnessReport,
    baseline: HarnessReport | None,
    gate_result: GateResult,
    thresholds_config: dict[str, Any],
) -> str:
    """Markdown listo para postear como PR comment."""
    lines: list[str] = []
    status_emoji = "✅" if gate_result.passed else "❌"
    status_text = "PASSED" if gate_result.passed else "FAILED"

    lines.append("# 📊 Harness Gate Report")
    lines.append("")
    lines.append(f"**Status:** {status_emoji} {status_text}  ")
    lines.append(f"**Run ID:** `{actual.run_id[:8]}`  ")
    lines.append(f"**Timestamp:** {actual.timestamp.isoformat()}  ")
    if baseline is not None:
        lines.append(f"**Baseline:** `{baseline.run_id[:8]}` ({baseline.timestamp.isoformat()})")
    else:
        lines.append("**Baseline:** _no disponible_ — sólo thresholds absolutos evaluados.")
    lines.append("")

    # Métricas vs Baseline
    lines.append("## Métricas vs Baseline")
    lines.append("")
    thresholds = thresholds_config.get("thresholds", {})
    rows: list[list[str]] = []
    violation_metrics = {v.metric for v in gate_result.violations}
    for metric_name, rule in thresholds.items():
        ttype = rule.get("type", "—")
        compared = gate_result.metrics_compared.get(metric_name, {})
        actual_val = compared.get("actual")
        baseline_val = compared.get("baseline")
        delta = None
        if (
            actual_val is not None
            and baseline_val is not None
            and baseline_val == baseline_val  # not NaN
        ):
            delta = actual_val - baseline_val
        status = "❌" if metric_name in violation_metrics else "✅"
        rows.append(
            [
                _metric_label(metric_name),
                _fmt(baseline_val),
                _fmt(actual_val),
                _fmt(delta) if delta is not None else "—",
                _threshold_label(rule, ttype),
                status,
            ]
        )
    lines.append(
        tabulate(
            rows,
            headers=["Métrica", "Baseline", "Actual", "Delta", "Threshold", "Status"],
            tablefmt="github",
        )
    )
    lines.append("")

    # Casos evaluados
    lines.append("## Casos evaluados")
    lines.append("")
    if not actual.per_case_results:
        lines.append("_(sin casos)_")
    else:
        for r in actual.per_case_results:
            err_suffix = f" — ❌ error: {r.error}" if r.error else ""
            lines.append(
                f"- `{r.case_id}`: factual_accuracy={r.factual_accuracy:.4f}, "
                f"omisiones={r.critical_omissions}, "
                f"hallucinations={r.hallucinations}{err_suffix}"
            )
    lines.append("")

    # Violaciones
    lines.append("## Violaciones")
    lines.append("")
    if not gate_result.violations:
        lines.append("_(ninguna — todas las métricas dentro de threshold)_")
    else:
        for v in gate_result.violations:
            lines.append(f"- ❌ **{_metric_label(v.metric)}** ({v.threshold_type})")
            lines.append(f"  - {v.message}")
    lines.append("")

    # Próximos pasos
    lines.append("## Próximos pasos")
    lines.append("")
    if gate_result.passed:
        lines.append("- Merge cuando el resto de checks estén verdes.")
        lines.append(
            "- Si querés actualizar el baseline canónico, abrir PR separado con label "
            "`baseline-update`."
        )
    else:
        lines.append("Si la regresión es aceptable y querés desbloquear el merge:")
        lines.append("")
        lines.append("1. Agregar label `skip-harness-gate` al PR.")
        lines.append("2. Documentar en la descripción del PR por qué se acepta la regresión.")
        lines.append("3. (Opcional) Abrir issue follow-up para investigar la caída.")
        lines.append("")
        lines.append(
            "Si la regresión NO es aceptable: revisar el diff y ajustar prompt / "
            "schema / lógica del extractor."
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("_Generado por sica-evals harness gate._")
    lines.append("")

    return "\n".join(lines)
