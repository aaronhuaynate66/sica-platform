"""Command-line interface for sica-evals.

Comandos:

    sica-eval run        Corre el harness, opcionalmente con gate vs baseline.
    sica-eval report     Renderiza un reporte JSON previamente persistido.
    sica-eval diff       Compara dos reportes JSON y muestra el delta.

Por default ``sica-eval run`` usa MockExtractor sobre ``*.expected.json``
para que el harness se pueda ejercitar en CI sin dependencias externas.
Pasar ``--extractor clinical`` (o el alias ``real``) para invocar al
extractor real (requiere ``ANTHROPIC_API_KEY``).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from tabulate import tabulate

from sica_evals.comparators.gate_comparator import (
    GateResult,
    evaluate_gate,
    load_thresholds,
)
from sica_evals.extractors import ClinicalExtractorWrapper, MockExtractor
from sica_evals.harness import SUPPORTED_FORMATS, Harness, diff_reports
from sica_evals.reporters import render_gate_report, render_markdown
from sica_evals.schemas import HarnessReport


def _safe_echo(text: str) -> None:
    """``click.echo`` con fallback ASCII para terminales Windows en cp1252.

    En CI (Linux/UTF-8) imprime con emojis. En consolas legacy que no
    soportan caracteres no-ASCII, reemplaza por `?` antes de imprimir.
    """
    try:
        click.echo(text)
    except UnicodeEncodeError:
        click.echo(text.encode("ascii", errors="replace").decode("ascii"))


def _default_fixtures_dir() -> Path:
    """Best-effort default for fixtures: ../fixtures relative to this file."""
    return (Path(__file__).resolve().parent.parent.parent / "fixtures").resolve()


def _default_output_dir() -> Path:
    """Best-effort default for output: ../reports."""
    return (Path(__file__).resolve().parent.parent.parent / "reports").resolve()


def _parse_case_filter(
    cases_csv: str | None,
    legacy_filter: str | None,
) -> list[str] | None:
    """Resuelve qué casos correr.

    Soporta:
      --cases "a,b,c"  → ["a", "b", "c"]
      --filter "a"     → ["a"]  (compat)
      ambos ausentes    → None (correr todos)
    """
    if cases_csv:
        ids = [c.strip() for c in cases_csv.split(",") if c.strip()]
        return ids or None
    if legacy_filter:
        return [legacy_filter]
    return None


def _build_extractor(
    kind: str,
    fixtures_dir: Path,
    case_ids: list[str] | None,
) -> tuple[object, str, str]:
    """Return (callable, extractor_version, model_used)."""
    # Alias: "real" → "clinical".
    if kind == "real":
        kind = "clinical"

    if kind == "mock":
        mock = MockExtractor()
        for expected_path in sorted(fixtures_dir.glob("*.expected.json")):
            case_id = expected_path.name.removesuffix(".expected.json")
            if case_ids and case_id not in case_ids:
                continue
            meta_path = fixtures_dir / f"{case_id}.expected.meta.json"
            pdf_path: Path = fixtures_dir / f"{case_id}.pdf"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                src = (meta.get("pdf_source") or {}).get("path")
                if src:
                    repo_root = _infer_repo_root(fixtures_dir)
                    pdf_path = (repo_root / src).resolve()
            expected = json.loads(expected_path.read_text(encoding="utf-8"))
            mock.register(pdf_path, expected)
        return mock, mock.extractor_version, mock.model_used

    if kind == "clinical":
        wrapper = ClinicalExtractorWrapper()
        wrapper._lazy_init()
        return wrapper, wrapper.extractor_version, wrapper.model_used

    msg = f"Unknown extractor kind: {kind!r}. Use 'mock', 'clinical' o 'real'."
    raise click.BadParameter(msg)


def _infer_repo_root(start: Path) -> Path:
    """Walk up from `start` looking for a .git directory."""
    cur = start.resolve()
    for _ in range(10):
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.parent.parent


def _run_for_case_ids(
    harness: Harness,
    case_ids: list[str] | None,
) -> HarnessReport:
    """Ejecuta el harness para uno o varios case_ids; agrega resultados."""
    if not case_ids:
        return harness.run_all()
    # ``run_all(filter_case_id=...)`` admite un único id. Para multiples,
    # cargamos casos manualmente y los corremos uno a uno.
    all_cases = harness.load_test_cases()
    wanted = [c for c in all_cases if c.case_id in case_ids]
    if not wanted:
        msg = (
            f"Ninguno de los case_ids solicitados existe en fixtures: {case_ids}. "
            f"Disponibles: {[c.case_id for c in all_cases]}"
        )
        raise click.BadParameter(msg)

    import platform
    import socket
    import uuid
    from datetime import UTC, datetime

    from sica_evals.harness import _git_commit_short
    from sica_evals.metrics import compute_calibration_error

    results = [harness.run_case(c) for c in wanted]
    succeeded = sum(1 for r in results if r.error is None)
    failed = len(results) - succeeded
    aggregate = {
        "factual_accuracy_mean": (
            round(sum(r.factual_accuracy for r in results) / max(len(results), 1), 4)
        ),
        "critical_omissions_total": float(sum(r.critical_omissions for r in results)),
        "hallucinations_total": float(sum(r.hallucinations for r in results)),
        "calibration_error_mean": compute_calibration_error(results),
        "latency_seconds_mean": (
            round(sum(r.latency_seconds for r in results) / max(len(results), 1), 4)
        ),
    }
    repo_root = harness._infer_repo_root()
    metadata = {
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "git_commit": _git_commit_short(repo_root),
        "extractor_version": harness.extractor_version,
        "model_used": harness.model_used,
        "fixtures_dir": str(harness.fixtures_dir),
        "case_ids_filter": ",".join(case_ids),
    }
    return HarnessReport(
        run_id=str(uuid.uuid4()),
        timestamp=datetime.now(UTC),
        cases_total=len(results),
        cases_succeeded=succeeded,
        cases_failed=failed,
        aggregate_metrics=aggregate,
        per_case_results=results,
        metadata=metadata,
    )


def _load_baseline(baseline_path: Path | None) -> HarnessReport | None:
    if baseline_path is None:
        return None
    if not baseline_path.exists():
        msg = f"Baseline no existe: {baseline_path}"
        raise click.BadParameter(msg)
    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    return HarnessReport.model_validate(data)


@click.group()
def main() -> None:
    """sica-evals — evaluation harness for SICA clinical extraction."""


@main.command()
@click.option(
    "--fixtures-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Directorio con *.expected.json (default: evals/fixtures).",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Directorio de salida para reportes (default: evals/reports).",
)
@click.option(
    "--extractor",
    "extractor_kind",
    type=click.Choice(["mock", "clinical", "real"], case_sensitive=False),
    default="mock",
    show_default=True,
    help="mock=fixtures sin red; clinical/real=llama al extractor real.",
)
@click.option(
    "--filter",
    "filter_case_id",
    default=None,
    help="(Compat) Corre solo un case_id; preferí --cases.",
)
@click.option(
    "--cases",
    "cases_csv",
    default=None,
    help="Lista de case_ids separados por coma (e.g. 'a,b,c').",
)
@click.option(
    "--format",
    "formats",
    type=click.Choice([*SUPPORTED_FORMATS, "all"]),
    multiple=True,
    default=("json",),
    show_default=True,
    help="Formato(s) del reporte. Repetir flag o usar 'all'.",
)
@click.option(
    "--output-format",
    "output_format",
    type=click.Choice(["json", "markdown", "gate"]),
    default=None,
    help=(
        "Atajo para --output-file: imprime el reporte en este formato. "
        "'gate' requiere --thresholds-file."
    ),
)
@click.option(
    "--output-file",
    "output_file",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Si se pasa, escribe el reporte (formato según --output-format) a este archivo.",
)
@click.option(
    "--baseline",
    "baseline_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path a un HarnessReport JSON previo (baseline canónico).",
)
@click.option(
    "--thresholds-file",
    "thresholds_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="YAML con thresholds del gate (e.g. .github/harness-thresholds.yaml).",
)
@click.option(
    "--fail-on-regression",
    is_flag=True,
    default=False,
    help="Si una métrica viola threshold, sys.exit(1). Requiere --thresholds-file.",
)
def run(
    fixtures_dir: Path | None,
    output_dir: Path | None,
    extractor_kind: str,
    filter_case_id: str | None,
    cases_csv: str | None,
    formats: tuple[str, ...],
    output_format: str | None,
    output_file: Path | None,
    baseline_path: Path | None,
    thresholds_file: Path | None,
    fail_on_regression: bool,
) -> None:
    """Run the harness, optionally evaluating a gate vs baseline."""
    fix = fixtures_dir or _default_fixtures_dir()
    out = output_dir or _default_output_dir()

    case_ids = _parse_case_filter(cases_csv, filter_case_id)
    extractor, ext_version, model_used = _build_extractor(extractor_kind, fix, case_ids)

    harness = Harness(
        extractor,  # type: ignore[arg-type]
        fixtures_dir=fix,
        output_dir=out,
        extractor_version=ext_version,
        model_used=model_used,
    )

    report = _run_for_case_ids(harness, case_ids)
    written = harness.save_report(report, formats=formats)

    click.echo(f"[sica-eval] run_id={report.run_id[:8]}")
    click.echo(
        f"[sica-eval] cases: total={report.cases_total} "
        f"ok={report.cases_succeeded} failed={report.cases_failed}"
    )
    for fmt, path in written.items():
        click.echo(f"[sica-eval] wrote {fmt} -> {path}")

    # ---------- Gate evaluation (opt-in) ----------
    gate_result: GateResult | None = None
    thresholds_config: dict | None = None
    baseline = _load_baseline(baseline_path)

    if thresholds_file is not None:
        thresholds_config = load_thresholds(thresholds_file)
        gate_result = evaluate_gate(report, baseline, thresholds_config)
        click.echo("")
        click.echo("[sica-eval] gate summary:")
        for line in gate_result.summary.splitlines():
            _safe_echo(f"  {line}")

    # ---------- Output file (opt-in) ----------
    if output_file is not None:
        chosen_format = output_format or ("gate" if thresholds_file else "markdown")
        rendered: str
        if chosen_format == "gate":
            if gate_result is None or thresholds_config is None:
                msg = "--output-format gate requiere --thresholds-file."
                raise click.BadParameter(msg)
            rendered = render_gate_report(report, baseline, gate_result, thresholds_config)
        elif chosen_format == "markdown":
            rendered = render_markdown(report)
        else:  # json
            rendered = json.dumps(report.model_dump(mode="json"), indent=2)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(rendered, encoding="utf-8")
        click.echo(f"[sica-eval] wrote {chosen_format} -> {output_file}")

    # ---------- Exit code policy ----------
    if report.cases_failed > 0:
        sys.exit(2)
    if fail_on_regression and gate_result is not None and not gate_result.passed:
        sys.exit(1)


@main.command()
@click.argument(
    "report_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def report(report_path: Path) -> None:
    """Render a stored JSON report as Markdown to stdout."""
    data = json.loads(report_path.read_text(encoding="utf-8"))
    hr = HarnessReport.model_validate(data)
    click.echo(render_markdown(hr))


@main.command()
@click.argument(
    "report_a",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.argument(
    "report_b",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def diff(report_a: Path, report_b: Path) -> None:
    """Compute delta between two JSON reports (B minus A)."""
    a = HarnessReport.model_validate(json.loads(report_a.read_text(encoding="utf-8")))
    b = HarnessReport.model_validate(json.loads(report_b.read_text(encoding="utf-8")))
    delta = diff_reports(a, b)

    click.echo("Aggregate delta (B - A):")
    click.echo(
        tabulate(
            sorted(delta["aggregate_delta"].items()),
            headers=["metric", "delta"],
            tablefmt="github",
            floatfmt=".4f",
        )
    )
    click.echo("")
    click.echo("Per-case delta:")
    rows = [
        [
            r["case_id"],
            r["factual_accuracy_delta"],
            r["critical_omissions_delta"],
            r["hallucinations_delta"],
        ]
        for r in delta["per_case_delta"]
    ]
    click.echo(
        tabulate(
            rows,
            headers=["case_id", "factual_delta", "omissions_delta", "hallu_delta"],
            tablefmt="github",
            floatfmt=".4f",
        )
    )


if __name__ == "__main__":
    main()
