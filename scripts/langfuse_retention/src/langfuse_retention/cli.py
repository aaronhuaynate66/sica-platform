"""CLI del script de retención.

Default: dry-run. Para borrar realmente, pasar ``--execute``.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict, replace
from pathlib import Path

import click

from langfuse_retention.cleanup import (
    config_from_env,
    run_cleanup,
)


@click.command()
@click.option(
    "--retention-days",
    default=None,
    type=int,
    help="Días de retención. Override de la env var LANGFUSE_RETENTION_DAYS.",
)
@click.option(
    "--execute",
    is_flag=True,
    default=False,
    help="Ejecutar deletes reales contra Langfuse. Default: dry-run.",
)
@click.option(
    "--output",
    "output_path",
    default=None,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path donde escribir el reporte JSON. Default: stdout.",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Log level DEBUG en stderr.",
)
def main(
    retention_days: int | None,
    execute: bool,
    output_path: Path | None,
    verbose: bool,
) -> None:
    """Cleanup de traces antiguas en Langfuse según política de retención.

    Política operativa documentada en ADR-0010.
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )

    base_config = config_from_env()
    # CLI flags ganan sobre env vars: dry_run viene de --execute (negado),
    # retention_days del --retention-days override.
    effective_config = replace(
        base_config,
        retention_days=retention_days if retention_days is not None else base_config.retention_days,
        dry_run=not execute,
    )

    click.echo(f"Modo: {'EXECUTE' if execute else 'DRY-RUN'}")
    click.echo(f"Retención: {effective_config.retention_days} días")
    click.echo(f"Base URL: {effective_config.base_url}")
    click.echo("")

    try:
        result = run_cleanup(effective_config)
    except ValueError as exc:
        click.echo(f"ERROR: {exc}", err=True)
        sys.exit(2)

    summary = asdict(result)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(summary, indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )
        click.echo(f"Reporte guardado: {output_path}")
    else:
        click.echo(json.dumps(summary, indent=2, default=str, ensure_ascii=False))

    if result.errors:
        click.echo(f"\n{len(result.errors)} errores. Revisar logs.", err=True)
        sys.exit(1)


# Alias para el entry point declarado en pyproject.toml
cli = main


if __name__ == "__main__":  # pragma: no cover
    main()
