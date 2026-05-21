"""CLI del clinical-extractor.

Uso:

    clinical-extractor extract path/to/file.pdf
    clinical-extractor extract path/to/file.pdf --output out.json
    clinical-extractor extract path/to/file.pdf --model claude-sonnet-4-5-20250929
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from clinical_extractor import __version__
from clinical_extractor.extractor import ExtractionError, extract_from_pdf
from clinical_extractor.prompts import ACTIVE_PROMPT_VERSION


@click.group()
@click.version_option(__version__, prog_name="clinical-extractor")
def cli() -> None:
    """clinical-extractor — SICA Multimodal Ingestion Layer (R0)."""
    load_dotenv()


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


if __name__ == "__main__":
    cli()
