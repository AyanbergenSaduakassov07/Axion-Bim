"""Command-line entry point. Every command calls services; no logic lives here."""

import typer

from axiom import __version__

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command()
def version() -> None:
    """Print the Axiom engine version."""
    typer.echo(__version__)


@app.callback()
def _root() -> None:
    """Axiom BIM: validate, score and compare IFC models."""
