"""Comparador de gates del harness — evalúa thresholds vs baseline.

Diseñado para CI:

- Lee un YAML con thresholds por métrica (ver ``.github/harness-thresholds.yaml``).
- Compara una corrida (``HarnessReport``) contra un baseline canónico
  (``HarnessReport`` previo persistido en ``evals/fixtures/baselines/``).
- Devuelve un ``GateResult`` con la lista exhaustiva de violaciones —
  no aborta al primer fallo (UX en CI: queremos ver todo lo roto).

Tipos de threshold soportados:

- ``relative_decline``: la métrica no puede caer más de ``max_decline_pp``
  puntos porcentuales (o unidades absolutas si la métrica no es %)
  respecto al baseline.
- ``absolute_max``: la métrica del run no puede superar ``max_value``.
- ``absolute_min``: la métrica del run no puede ser menor a ``min_value``.

Convención de signos: para "métricas buenas más altas" (accuracy),
``relative_decline`` mide ``baseline - actual``. Para "métricas malas más
altas" (omissions, hallucinations), se usa ``absolute_max`` siempre.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from sica_evals.schemas import HarnessReport


@dataclass(frozen=True)
class Violation:
    """Una violación específica de threshold."""

    metric: str
    threshold_type: str
    expected: float
    actual: float
    delta: float
    message: str


@dataclass
class GateResult:
    """Resultado consolidado de evaluar el gate."""

    passed: bool
    violations: list[Violation] = field(default_factory=list)
    summary: str = ""
    metrics_compared: dict[str, dict[str, float]] = field(default_factory=dict)


def load_thresholds(thresholds_path: Path) -> dict[str, Any]:
    """Carga el YAML de thresholds y devuelve su dict crudo.

    Estructura esperada:
        thresholds:
          factual_accuracy:
            type: "relative_decline"
            max_decline_pp: 3.0
            description: "..."
        config:
          baseline_path: "..."
          fail_fast: false
    """
    if not thresholds_path.exists():
        msg = f"Thresholds file no existe: {thresholds_path}"
        raise FileNotFoundError(msg)
    raw = yaml.safe_load(thresholds_path.read_text(encoding="utf-8")) or {}
    if "thresholds" not in raw:
        msg = (
            f"Thresholds file {thresholds_path} no tiene clave 'thresholds'. "
            "Ver evals/fixtures/baselines/README.md para el formato esperado."
        )
        raise ValueError(msg)
    return raw


def _metric_value(report: HarnessReport, metric_key: str) -> float | None:
    """Mapea nombres de threshold a claves de ``aggregate_metrics``.

    Aliases pensados para que el YAML sea legible — el threshold yaml
    habla en términos humanos ("factual_accuracy") mientras que el report
    persiste claves técnicas ("factual_accuracy_mean").
    """
    aliases = {
        "factual_accuracy": "factual_accuracy_mean",
        "critical_omissions": "critical_omissions_total",
        "hallucination_count": "hallucinations_total",
        "hallucinations": "hallucinations_total",
        "ece": "calibration_error_mean",
        "calibration_error": "calibration_error_mean",
        "latency_seconds": "latency_seconds_mean",
    }
    key = aliases.get(metric_key, metric_key)
    val = report.aggregate_metrics.get(key)
    if val is None:
        return None
    return float(val)


def evaluate_gate(
    actual: HarnessReport,
    baseline: HarnessReport | None,
    thresholds_config: dict[str, Any],
) -> GateResult:
    """Evalúa todos los thresholds y devuelve violations.

    Si ``baseline`` es None, sólo se evalúan thresholds de tipo
    ``absolute_max`` / ``absolute_min`` (no se puede medir decline sin
    referencia). Se reporta como WARN en el summary.
    """
    thresholds: dict[str, dict[str, Any]] = thresholds_config.get("thresholds", {})
    violations: list[Violation] = []
    metrics_compared: dict[str, dict[str, float]] = {}

    for metric_name, rule in thresholds.items():
        ttype = rule.get("type")
        actual_val = _metric_value(actual, metric_name)
        baseline_val = (
            _metric_value(baseline, metric_name) if baseline is not None else None
        )

        if actual_val is None:
            # Métrica ausente en el run actual — no fallar pero registrar.
            violations.append(
                Violation(
                    metric=metric_name,
                    threshold_type=ttype or "unknown",
                    expected=float("nan"),
                    actual=float("nan"),
                    delta=float("nan"),
                    message=(
                        f"Métrica '{metric_name}' no presente en el report "
                        f"actual (revisar aggregate_metrics)."
                    ),
                )
            )
            continue

        metrics_compared[metric_name] = {
            "actual": actual_val,
            "baseline": baseline_val if baseline_val is not None else float("nan"),
        }

        if ttype == "relative_decline":
            if baseline_val is None:
                continue  # no referencia, skip silencioso
            # Convención: ``max_decline_pp`` se expresa en puntos porcentuales
            # (3.0 pp = 0.03 en escala [0,1]). Las métricas tipo accuracy/ECE
            # viven en [0,1], así que dividimos entre 100 para obtener la
            # tolerancia absoluta en la misma escala.
            max_decline_pp = float(rule.get("max_decline_pp", 0.0))
            max_decline = max_decline_pp / 100.0
            # decline = baseline - actual; positivo = empeoró
            decline = baseline_val - actual_val
            metrics_compared[metric_name]["delta"] = -decline  # delta firmado
            if decline > max_decline:
                violations.append(
                    Violation(
                        metric=metric_name,
                        threshold_type=ttype,
                        expected=baseline_val,
                        actual=actual_val,
                        delta=-decline,
                        message=(
                            f"{metric_name} cayó {decline * 100:.2f}pp respecto al "
                            f"baseline ({baseline_val:.4f} → {actual_val:.4f}); "
                            f"máximo permitido: {max_decline_pp:.2f}pp."
                        ),
                    )
                )
        elif ttype == "absolute_max":
            max_value = float(rule.get("max_value", 0.0))
            metrics_compared[metric_name]["threshold"] = max_value
            if actual_val > max_value:
                violations.append(
                    Violation(
                        metric=metric_name,
                        threshold_type=ttype,
                        expected=max_value,
                        actual=actual_val,
                        delta=actual_val - max_value,
                        message=(
                            f"{metric_name} = {actual_val} excede el máximo "
                            f"permitido ({max_value})."
                        ),
                    )
                )
        elif ttype == "absolute_min":
            min_value = float(rule.get("min_value", 0.0))
            metrics_compared[metric_name]["threshold"] = min_value
            if actual_val < min_value:
                violations.append(
                    Violation(
                        metric=metric_name,
                        threshold_type=ttype,
                        expected=min_value,
                        actual=actual_val,
                        delta=actual_val - min_value,
                        message=(
                            f"{metric_name} = {actual_val} por debajo del mínimo "
                            f"requerido ({min_value})."
                        ),
                    )
                )
        else:
            violations.append(
                Violation(
                    metric=metric_name,
                    threshold_type=str(ttype),
                    expected=float("nan"),
                    actual=actual_val,
                    delta=float("nan"),
                    message=(
                        f"Threshold type '{ttype}' no soportado para "
                        f"métrica '{metric_name}'. Tipos válidos: "
                        f"relative_decline, absolute_max, absolute_min."
                    ),
                )
            )

    passed = len(violations) == 0
    summary = _build_summary(passed, violations, baseline is not None)
    return GateResult(
        passed=passed,
        violations=violations,
        summary=summary,
        metrics_compared=metrics_compared,
    )


def _build_summary(passed: bool, violations: list[Violation], has_baseline: bool) -> str:
    """Mensaje humano corto para logs / step summary de CI."""
    if passed:
        if not has_baseline:
            return "✅ Gate PASSED (sin baseline — sólo se evaluaron thresholds absolutos)."
        return "✅ Gate PASSED — todas las métricas dentro de threshold."
    lines = [f"❌ Gate FAILED — {len(violations)} violación(es):"]
    for v in violations:
        lines.append(f"  - {v.message}")
    return "\n".join(lines)
