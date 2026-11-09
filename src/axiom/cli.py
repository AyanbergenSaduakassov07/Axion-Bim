"""Command-line entry point. Commands call library/services functions; no logic lives here."""

import json
import logging
import time
from pathlib import Path

import typer

from axiom import __version__
from axiom.extract import extract, profile

app = typer.Typer(no_args_is_help=True, add_completion=False)
ExistingFile = typer.Argument(..., exists=True, dir_okay=False, readable=True)


@app.callback()
def _root(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Axiom BIM: validate, score and compare IFC models."""
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING, format="%(levelname)s %(message)s"
    )


@app.command()
def version() -> None:
    """Print the Axiom engine version."""
    typer.echo(__version__)


@app.command()
def inspect(path: Path = ExistingFile, as_json: bool = typer.Option(False, "--json")) -> None:
    """Extract an IFC file and print its metadata and data-completeness profile."""
    start = time.perf_counter()
    snap = extract(path)
    prof = profile(snap)
    elapsed = time.perf_counter() - start
    if as_json:
        typer.echo(
            json.dumps(
                {"meta": snap.meta.model_dump(mode="json"), "profile": prof, "seconds": round(elapsed, 3)},
                indent=2,
            )
        )
        return
    m = snap.meta
    typer.echo(f"{path.name}  {m.schema_name}  {m.authoring_app or '-'}  project={m.project_name or '-'}")
    typer.echo(f"length unit x{m.length_scale:g} -> m  sha256 {m.file_sha256[:12]}  {m.file_size:,} bytes")
    typer.echo(f"{prof['total_elements']} elements  completeness {prof['completeness']}  ({elapsed:.2f}s)")
    typer.echo(
        f"{'class':<28}{'n':>6}  "
        + "  ".join(f"{k:>11}" for k in ("name", "psets", "material", "geometry", "containment"))
    )
    for cls, c in prof["by_class"].items():
        cells = "  ".join(f"{'-' if v is None else v:>11}" for v in c["missing"].values())
        typer.echo(f"{cls:<28}{c['count']:>6}  {cells}")
