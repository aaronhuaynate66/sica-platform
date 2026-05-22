"""CLI del clinical-extractor.

Comandos:

    clinical-extractor extract path/to/file.pdf
    clinical-extractor extract path/to/file.pdf --output out.json
    clinical-extractor extract path/to/file.pdf --model claude-sonnet-4-5-20250929
    clinical-extractor extract-batch path/to/directory/
    clinical-extractor extract-batch path/to/directory/ --output-dir out/ --concurrency 3

`extract-batch` procesa todos los `*.pdf` del directorio en paralelo
limitado (default: 3 PDFs concurrentes). Por cada `foo.pdf` produce un
`foo.json` con el `ObstetricSummary` extraído.

La telemetría (JSON-line) sale por stderr en todos los comandos.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import click
from dotenv import load_dotenv

from clinical_extractor import __version__, telemetry
from clinical_extractor.extractor import ExtractionError, extract_from_pdf
from clinical_extractor.prompts import ACTIVE_PROMPT_VERSION


@click.group()
@click.version_option(__version__, prog_name="clinical-extractor")
def cli() -> None:
    """clinical-extractor — SICA Multimodal Ingestion Layer (R0)."""
    load_dotenv()
    telemetry.configure_stream_handler()


@cli.command()
@click.argument(
    "pdf_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=None,
    help="Ruta donde escribir el JSON. Si se omite, imprime a stdout.",
)
@click.option(
    "--model",
    type=str,
    default=None,
    help="Override del modelo Claude. Default: variable env CLAUDE_MODEL.",
)
@click.option(
    "--max-tokens",
    type=int,
    default=None,
    help="Override del max_tokens. Default: variable env CLAUDE_MAX_TOKENS.",
)
@click.option(
    "--pretty/--compact",
    default=True,
    help="Pretty-print del JSON (default) o JSON compacto.",
)
def extract(
    pdf_path: Path,
    output: Path | None,
    model: str | None,
    max_tokens: int | None,
    pretty: bool,
) -> None:
    """Extrae un resumen obstétrico estructurado desde PDF_PATH."""
    click.echo(f"⟶ extracting {pdf_path}", err=True)
    click.echo(f"  prompt version: {ACTIVE_PROMPT_VERSION}", err=True)

    try:
        summary = extract_from_pdf(pdf_path, model=model, max_tokens=max_tokens)
    except ExtractionError as exc:
        click.echo(f"✗ ExtractionError: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"✗ Error inesperado: {exc}", err=True)
        sys.exit(2)

    indent = 2 if pretty else None
    payload = summary.model_dump(mode="json")
    rendered = json.dumps(payload, indent=indent, ensure_ascii=False, sort_keys=True)

    if output is not None:
        output.write_text(rendered + "\n", encoding="utf-8")
        click.echo(f"✓ output: {output}", err=True)
    else:
        click.echo(rendered)

    click.echo(f"  confidence_score: {summary.confidence_score:.2f}", err=True)
    click.echo(f"  evidence_spans: {len(summary.evidence_spans)}", err=True)


# =========================================================================
# extract-batch — procesamiento paralelo de un directorio
# =========================================================================


async def _extract_one(
    pdf_path: Path,
    output_dir: Path,
    semaphore: asyncio.Semaphore,
    model: str | None,
    max_tokens: int | None,
) -> tuple[Path, Path | None, str | None, float]:
    """Procesa un PDF. Devuelve (pdf, output_json|None, error|None, elapsed_s)."""
    async with semaphore:
        started = time.perf_counter()
        try:
            summary = await asyncio.to_thread(
                extract_from_pdf, pdf_path, model=model, max_tokens=max_tokens
            )
        except ExtractionError as exc:
            elapsed = time.perf_counter() - started
            return pdf_path, None, f"ExtractionError: {exc}", elapsed
        except Exception as exc:  # noqa: BLE001 — surface every failure in summary
            elapsed = time.perf_counter() - started
            return pdf_path, None, f"{type(exc).__name__}: {exc}", elapsed

        elapsed = time.perf_counter() - started
        out_json = output_dir / f"{pdf_path.stem}.json"
        payload = summary.model_dump(mode="json")
        out_json.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return pdf_path, out_json, None, elapsed


async def _run_batch(
    pdfs: list[Path],
    output_dir: Path,
    concurrency: int,
    model: str | None,
    max_tokens: int | None,
) -> list[tuple[Path, Path | None, str | None, float]]:
    semaphore = asyncio.Semaphore(concurrency)
    tasks = [
        _extract_one(pdf, output_dir, semaphore, model, max_tokens) for pdf in pdfs
    ]
    return await asyncio.gather(*tasks)


@cli.command("extract-batch")
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, readable=True, path_type=Path),
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, writable=True, path_type=Path),
    default=None,
    help="Directorio de salida para los JSONs. Default: mismo que DIRECTORY.",
)
@click.option(
    "--concurrency",
    type=click.IntRange(min=1, max=8),
    default=3,
    show_default=True,
    help="Máximo de PDFs procesados en paralelo (asyncio.Semaphore).",
)
@click.option(
    "--pattern",
    type=str,
    default="*.pdf",
    show_default=True,
    help="Glob pattern dentro de DIRECTORY.",
)
@click.option(
    "--model",
    type=str,
    default=None,
    help="Override del modelo Claude.",
)
@click.option(
    "--max-tokens",
    type=int,
    default=None,
    help="Override del max_tokens.",
)
def extract_batch(
    directory: Path,
    output_dir: Path | None,
    concurrency: int,
    pattern: str,
    model: str | None,
    max_tokens: int | None,
) -> None:
    """Procesa en paralelo todos los PDFs de DIRECTORY → un JSON por PDF."""
    pdfs = sorted(directory.glob(pattern))
    if not pdfs:
        click.echo(f"⚠  No se encontraron PDFs en {directory} (pattern={pattern!r})", err=True)
        sys.exit(0)

    out_dir = output_dir or directory
    out_dir.mkdir(parents=True, exist_ok=True)

    click.echo(
        f"⟶ extract-batch: {len(pdfs)} PDFs, concurrency={concurrency}, "
        f"output_dir={out_dir}",
        err=True,
    )

    started = time.perf_counter()
    results = asyncio.run(_run_batch(pdfs, out_dir, concurrency, model, max_tokens))
    total_elapsed = time.perf_counter() - started

    succeeded: list[tuple[Path, Path]] = []
    failed: list[tuple[Path, str]] = []
    for pdf, out_json, error, _elapsed in results:
        if error is None and out_json is not None:
            succeeded.append((pdf, out_json))
        else:
            failed.append((pdf, error or "unknown error"))

    click.echo("", err=True)
    click.echo(f"=== resumen extract-batch ===", err=True)
    click.echo(f"  procesados: {len(results)}", err=True)
    click.echo(f"  exitosos:   {len(succeeded)}", err=True)
    click.echo(f"  fallidos:   {len(failed)}", err=True)
    click.echo(f"  tiempo:     {total_elapsed:.2f}s", err=True)

    if succeeded:
        click.echo("  outputs:", err=True)
        for pdf, out in succeeded:
            click.echo(f"    {pdf.name} → {out.name}", err=True)
    if failed:
        click.echo("  errores:", err=True)
        for pdf, err in failed:
            click.echo(f"    {pdf.name}: {err}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
