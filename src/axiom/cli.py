"""Command-line entry point. Commands call library/services functions; no logic lives here."""

import json
import logging
import time
from dataclasses import asdict
from pathlib import Path

import typer

from axiom import __version__
from axiom.config import load_settings
from axiom.extract import extract, profile
from axiom.findings import CheckStatus
from axiom.repo.db import get_engine, migrate
from axiom.score import MhiResult
from axiom.services import audits, projects, revisions

app = typer.Typer(no_args_is_help=True, add_completion=False)
STATUSES = [s.value for s in CheckStatus]
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


@app.command()
def audit(
    path: Path = ExistingFile,
    project: str = typer.Option("local", help="Project to file the model under."),
    model: str | None = typer.Option(None, help="Model name; defaults to the file stem."),
    json_out: Path | None = typer.Option(None, "--json", help="Write the full JSON report here."),
    ids: Path | None = typer.Option(
        None, "--ids", exists=True, dir_okay=False, readable=True, help="Also check this IDS file."
    ),
) -> None:
    """Ingest (if new) and audit an IFC file with the built-in rules (and an IDS file, if given)."""
    settings = load_settings()
    engine = get_engine(settings.db_url)
    migrate(engine)
    model_id = projects.ensure_model(engine, project, model or path.stem)
    ingested = revisions.ingest(engine, model_id, path, files_dir=settings.files_dir)
    try:
        result = audits.run_audit(engine, ingested.revision_id, ids_path=ids, files_dir=settings.files_dir)
    except ValueError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(2) from e
    typer.echo(
        f"revision {ingested.seq} ({'new' if ingested.created else 'already ingested'})  "
        f"audit #{result.audit_run_id}  ruleset {result.reproducibility['ruleset_version']}"
    )
    width = max(9, *(len(k) + 1 for k in result.counts))
    typer.echo(f"{'rule':<{width}}" + "".join(f"{s:>15}" for s in STATUSES))
    for rule_id, counts in result.counts.items():
        typer.echo(f"{rule_id:<{width}}" + "".join(f"{counts.get(s, 0):>15}" for s in STATUSES))
    for f in result.findings:
        typer.echo(f"  {f.severity:<8} {f.rule_id}  {f.element_name or f.global_id or '-':<16} {f.message}")
        if f.expected or f.actual:
            typer.echo(f"           expected: {f.expected or '-'}  |  actual: {f.actual or '-'}")
    _print_mhi(result.mhi)
    if json_out:
        report = {
            "mhi": asdict(result.mhi),
            "reproducibility": result.reproducibility,
            "counts": result.counts,
            "findings": [f.model_dump(mode="json") for f in result.findings],
        }
        json_out.write_text(json.dumps(report, indent=2))
        typer.echo(f"report written to {json_out}")


def _fmt(v: float | None, spec: str = ">7.1f") -> str:
    return f"{'-':>7}" if v is None else format(v, spec)


def _print_mhi(mhi: MhiResult) -> None:
    gate = f"BLOCKED by {len(mhi.blocking)} critical finding(s)" if mhi.blocked else "not blocked"
    typer.echo(f"MHI {_fmt(mhi.score, '.1f').strip()}  coverage {_fmt(mhi.coverage, '.0f').strip()}%  {gate}")
    typer.echo(f"  {'dimension':<24}{'score':>7}{'weight':>8}{'contrib':>9}{'coverage':>10}")
    for name, d in mhi.dimensions.items():
        cov = _fmt(d.coverage, ">9.0f")
        typer.echo(f"  {name:<24}{_fmt(d.score)}{d.effective_weight:>8.2f}{d.contribution:>9.1f}{cov}%")
    for note in mhi.notes:
        typer.echo(f"  note: {note}")
