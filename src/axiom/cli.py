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
from axiom.services import audits, comparisons, projects, quantities, reports, revisions
from axiom.services import gate as gate_service
from axiom.services.comparisons import ComparisonResult

app = typer.Typer(no_args_is_help=True, add_completion=False)
STATUSES = [s.value for s in CheckStatus]
ExistingFile = typer.Argument(..., exists=True, dir_okay=False, readable=True)
GeometryOption = typer.Option(False, "--geometry", help="Also compute volumes from geometry (slower).")
IdsOption = typer.Option(
    None, "--ids", exists=True, dir_okay=False, readable=True, help="Also check this IDS file."
)


@app.callback()
def _root(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Axiom BIM: validate, score and compare IFC models."""
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING, format="%(levelname)s %(message)s"
    )


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind address; keep local unless behind a proxy."),
    port: int = typer.Option(8000),
) -> None:
    """Run the HTTP API (docs at /docs) with the background job runner."""
    import uvicorn  # noqa: PLC0415  (server deps load only for this command)

    from axiom.api import create_app  # noqa: PLC0415

    uvicorn.run(create_app(), host=host, port=port)


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
    *,
    project: str = typer.Option("local", help="Project to file the model under."),
    model: str | None = typer.Option(None, help="Model name; defaults to the file stem."),
    json_out: Path | None = typer.Option(None, "--json", help="Write the full JSON report here."),
    ids: Path | None = IdsOption,
    geometry: bool = GeometryOption,
    gate: bool = typer.Option(False, "--gate", help="Exit 1 unless the delivery would be accepted."),
) -> None:
    """Ingest (if new) and audit an IFC file with the built-in rules (and an IDS file, if given)."""
    engine, model_id = _open(project, model or path.stem)
    ingested, result = _ingest_and_audit(engine, model_id, path, ids, geometry)
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
    if (cmp := comparisons.compare_with_previous(engine, ingested.revision_id)) is not None:
        _print_comparison(engine, cmp, events=False)
    if json_out:
        report = {
            "mhi": asdict(result.mhi),
            "reproducibility": result.reproducibility,
            "counts": result.counts,
            "findings": [f.model_dump(mode="json") for f in result.findings],
        }
        json_out.write_text(json.dumps(report, indent=2))
        typer.echo(f"report written to {json_out}")
    decision = gate_service.audit_gate(engine, result.audit_run_id)
    reasons = ", ".join(r["code"] + (f"={r['n']}" if "n" in r else "") for r in decision["reasons"])
    typer.echo(f"delivery decision: {decision['decision']}" + (f" ({reasons})" if reasons else ""))
    if gate and not decision["decision"].startswith("accepted"):
        raise typer.Exit(1)


@app.command()
def compare(
    paths: list[Path] = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    project: str = typer.Option("local", help="Project to file the model under."),
    model: str | None = typer.Option(None, help="Model name; defaults to the first file's stem."),
    ids: Path | None = IdsOption,
    json_out: Path | None = typer.Option(None, "--json", help="Write the comparisons as JSON here."),
) -> None:
    """Audit two or more revisions of one model (in order) and compare each with the one before."""
    if len(paths) < 2:
        typer.echo("error: compare needs at least two IFC files", err=True)
        raise typer.Exit(2)
    engine, model_id = _open(project, model or paths[0].stem)
    revs = [_ingest_and_audit(engine, model_id, p, ids)[0].revision_id for p in paths]
    results = [comparisons.compare(engine, a, b) for a, b in zip(revs, revs[1:], strict=False)]
    for r in results:
        _print_comparison(engine, r, events=True)
    if json_out:
        json_out.write_text(json.dumps([_comparison_json(r) for r in results], indent=2, default=str))
        typer.echo(f"report written to {json_out}")


@app.command()
def report(
    audit_id: int = typer.Argument(..., help="Audit number, as printed by `axiom audit`."),
    fmt: str = typer.Option("json", "--format", help="json | csv | html | bcf (BCF 3.0 zip, needs --out)."),
    comparison: int | None = typer.Option(None, help="Comparison to include; default: the latest one."),
    out: Path | None = typer.Option(None, "--out", help="Write here instead of stdout."),
) -> None:
    """Render a stored audit as a report (no re-processing of the IFC file)."""
    engine = get_engine(load_settings().db_url)
    migrate(engine)
    try:
        body = reports.render(reports.build(engine, audit_id, comparison), fmt)
    except (LookupError, ValueError) as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(2) from e
    if isinstance(body, bytes):
        if out is None:
            typer.echo("error: --format bcf is a zip archive; pass --out FILE.bcf", err=True)
            raise typer.Exit(2)
        out.write_bytes(body)
    elif out is None:
        typer.echo(body)
        return
    else:
        out.write_text(body, encoding="utf-8")
    typer.echo(f"report written to {out}")


@app.command(name="quantities")
def quantities_cmd(
    path: Path = ExistingFile,
    *,
    by: str = typer.Option("class", help="Group by class | storey | material | classification."),
    geometry: bool = GeometryOption,
    against: Path | None = typer.Option(
        None, exists=True, dir_okay=False, readable=True, help="Earlier revision: also print totals delta."
    ),
    project: str = typer.Option("local"),
    model: str | None = typer.Option(None, help="Model name; defaults to the file stem."),
    json_out: Path | None = typer.Option(None, "--json", help="Write rows (and delta) as JSON here."),
) -> None:
    """Quantity totals per group from Qto sets (and geometry, if asked); never summed across methods."""
    engine, model_id = _open(project, model or path.stem)
    files_dir = load_settings().files_dir
    head = revisions.ingest(engine, model_id, path, files_dir=files_dir).revision_id
    base = revisions.ingest(engine, model_id, against, files_dir=files_dir).revision_id if against else None
    try:
        rows = quantities.report(engine, head, by, geometry=geometry, files_dir=files_dir)
        delta = (
            quantities.delta(engine, base, head, by, geometry=geometry, files_dir=files_dir) if base else ()
        )
    except ValueError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(2) from e
    _print_quantities(rows, {(d.group, d.qto, d.quantity, d.method): d for d in delta})
    if json_out:
        report = {"rows": [asdict(r) for r in rows], "delta": [asdict(d) for d in delta]}
        json_out.write_text(json.dumps(report, indent=2))
        typer.echo(f"report written to {json_out}")


def _print_quantities(rows, delta: dict) -> None:
    typer.echo(
        f"{'group':<22}{'quantity':<42}{'method':<10}{'total':>14} {'unit':<5}{'n':>5}{'missing':>8}  delta"
    )
    for r in rows:
        d = delta.get((r.group, r.qto, r.quantity, r.method))
        change = "" if d is None or d.old == d.new else f"{(d.new or 0) - (d.old or 0):+.4g}"
        name = f"{r.qto}.{r.quantity}"
        typer.echo(
            f"{r.group[:21]:<22}{name[:41]:<42}{r.method:<10}{r.total:>14.4f} {r.unit or '-':<5}"
            f"{r.count:>5}{len(r.missing):>8}  {change}"
        )


def _open(project: str, model: str):
    settings = load_settings()
    engine = get_engine(settings.db_url)
    migrate(engine)
    return engine, projects.ensure_model(engine, project, model)


def _ingest_and_audit(engine, model_id: int, path: Path, ids: Path | None, geometry: bool = False):
    files_dir = load_settings().files_dir
    ingested = revisions.ingest(engine, model_id, path, files_dir=files_dir)
    try:
        return ingested, audits.run_audit(
            engine, ingested.revision_id, ids_path=ids, files_dir=files_dir, geometry=geometry
        )
    except ValueError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(2) from e


def _print_comparison(engine, r: ComparisonResult, *, events: bool) -> None:
    base, head = (
        revisions.revision_seq(engine, r.base_revision_id),
        revisions.revision_seq(engine, r.head_revision_id),
    )
    s, m = r.summary, r.summary["mhi"]
    delta = "-" if m["delta"] is None else f"{m['delta']:+.1f}"
    label = f"revision {base} -> {head}" if events else f"vs revision {base}:"
    changes = ", ".join(f"{k} {v}" for k, v in sorted(s["changes"].items())) or "no element changes"
    mhi = f"{_fmt(m['base'], '.1f').strip()} -> {_fmt(m['head'], '.1f').strip()} ({delta})"
    typer.echo(f"{label}  {changes}  |  MHI {mhi}")
    typer.echo("  events: " + ", ".join(f"{k} {v}" for k, v in sorted(s["events"].items())))
    for flag, text in (("ids_mismatch", "IDS file differs"), ("ruleset_mismatch", "rule set differs")):
        if s[flag]:
            typer.echo(f"  warning: {text} between the two audits; affected events are uncertain")
    if r.diff.identity_unstable:
        classes = ", ".join(s["unstable_classes"])
        typer.echo(f"  warning: GlobalIds look regenerated for {classes}; all events uncertain")
    moved = [f"{k} {v:+.1f}" for k, v in m["dimensions"].items() if round(v, 1)]
    if moved:
        typer.echo("  MHI by dimension: " + ", ".join(moved))
    if events:
        _print_events(r)


def _print_events(r: ComparisonResult) -> None:
    for cls, kinds in r.summary["changes_by_class"].items():
        typer.echo(f"  {cls:<20} " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))
    why = {(i["global_id"], i["rule_id"]): ", ".join(i["paths"]) for i in r.summary["impact"]}
    for e in r.events:
        if e.event == "persistent":
            continue
        cause = why.get((e.global_id, e.rule_id))
        detail = f"<- {cause} changed" if cause else (e.note or "")
        typer.echo(f"  {e.event:<10} {e.rule_id:<14} {e.element_name or e.global_id or '-':<8} {detail}")


def _comparison_json(r: ComparisonResult) -> dict:
    return {
        "comparison_id": r.comparison_id,
        "base_revision_id": r.base_revision_id,
        "head_revision_id": r.head_revision_id,
        "summary": r.summary,
        "changes": [asdict(c) for c in r.diff.changes],
        "events": [asdict(e) for e in r.events],
    }


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
