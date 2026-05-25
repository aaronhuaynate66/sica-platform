"""Command-line interface for sica-evals.

Two main commands:

    sica-eval run        Run the harness against fixtures and write a report.
    sica-eval report     Pretty-print a previously generated report.
    sica-eval diff       Compare two JSON reports and surface regressions.

By default `sica-eval run` uses the MockExtractor against
`{case_id}.expected.json` so the harness can be exercised in CI without
external dependencies. Pass `--extractor clinical` to drive the real
clinical-extractor service (requires ANTHROPIC_API_KEY).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from tabulate import tabulate

from sica_evals.extractors import ClinicalExtractorWrapper, MockExtractor
from sica_evals.harness import SUPPORTED_FORMATS, Harness, diff_reports
from sica_evals.reporters import render_markdown
from sica_evals.schemas import HarnessReport


def _default_fixtures_dir() -> Path:
    """Best-effort default for fixtures: ../fixtures relative to this file."""
    return (Path(__file__).resolve().parent.parent.parent / "fixtures").resolve()


def _default_output_dir() -> Path:
    """Best-effort default for output: ../reports."""
    return (Path(__file__).resolve().parent.parent.parent / "reports").resolve()


def _build_extractor(
    kind: str,
    fixtures_dir: Path,
    filter_case_id: str | None,
) -> tuple[object, str, str]:
    """Return (callable, extractor_version, model_used)."""
    if kind == "mock":
        # Pre-load every expected.json as the mock output for its case.
        mock = MockExtractor()
        for expected_path in sorted(fixtures_dir.glob("*.expected.json")):
            case_id = expected_path.name.removesuffix(".expected.json")
            if filter_case_id and case_id != filter_case_id:
                continue
            meta_path = fixtures_dir / f"{case_id}.expected.meta.json"
            pdf_path: Path = fixtures_dir / f"{case_id}.pdf"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                src = (meta.get("pdf_source") or {}).get("path")
                if src:
                    # Resolve relative to repo root inferred from fixtures dir.
                    repo_root = _infer_repo_root(fixtures_dir)
                    pdf_path = (repo_root / src).resolve()
            expected = json.loads(expected_path.read_text(encoding="utf-8"))
            mock.register(pdf_path, expected)
        return mock, mock.extractor_version, mock.model_used

    if kind == "clinical":
        wrapper = ClinicalExtractorWrapper()
        # Force lazy init now so extractor_version and model_used are populated
        # from the actual clinical_extractor package metadata, not from the
        # "unknown" placeholders set in ClinicalExtractorWrapper.__init__.
        wrapper._lazy_init()
        return wrapper, wrapper.extractor_version, wrapper.model_used

    msg = f"Unknown extractor kind: {kind!r}. Use 'mock' or 'clinical'."
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
    type=click.Choice(["mock", "clinical"], case_sensitive=False),
    default="mock",
    show_default=True,
    help="Mock = devuelve fixtures sin llamar al modelo. Clinical = llama al extractor real.",
)
@click.option(
    "--filter",
    "filter_case_id",
    default=None,
    help="Corre solo el case_id indicado.",
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
def run(
    fixtures_dir: Path | None,
    output_dir: Path | None,
    extractor_kind: str,
    filter_case_id: str | None,
    formats: tuple[str, ...],
) -> None:
    """Run the harness against the fixtures directory."""
    fix = fixtures_dir or _default_fixtures_dir()
    out = output_dir or _default_output_dir()

    extractor, ext_version, model_used = _build_extractor(
        extractor_kind, fix, filter_case_id
    )

    harness = Harness(
        extractor,  # type: ignore[arg-type]
        fixtures_dir=fix,
        output_dir=out,
        extractor_version=ext_version,
        model_used=model_used,
    )
    report = harness.run_all(filter_case_id=filter_case_id)
    written = harness.save_report(report, formats=formats)

    click.echo(f"[sica-eval] run_id={report.run_id[:8]}")
    click.echo(
        f"[sica-eval] cases: total={report.cases_total} "
        f"ok={report.cases_succeeded} failed={report.cases_failed}"
    )
    for fmt, path in written.items():
        click.echo(f"[sica-eval] wrote {fmt} -> {path}")

    # Exit non-zero if any case failed to run. Quality gate is informational.
    if report.cases_failed > 0:
        sys.exit(2)


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
        [r["case_id"], r["factual_accuracy_delta"], r["critical_omissions_delta"], r["hallucinations_delta"]]
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
