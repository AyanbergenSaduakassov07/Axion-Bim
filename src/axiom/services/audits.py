"""Audit a stored revision: rules -> findings + per-rule counts, persisted with a reproducibility block."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine

from axiom import __version__
from axiom.extract import file_sha256
from axiom.findings import Finding
from axiom.ids import run_ids
from axiom.repo import audits as repo
from axiom.rules import run_rules
from axiom.rules.engine import AuditOutput
from axiom.score import MhiResult, ScoringConfig, compute_mhi, load_config
from axiom.services.revisions import load_snapshot, store_file

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuditResult:
    audit_run_id: int
    revision_id: int
    findings: tuple[Finding, ...]
    counts: dict[str, dict[str, int]]
    reproducibility: dict
    mhi: MhiResult


def run_audit(
    engine: Engine,
    revision_id: int,
    *,
    ids_path: Path | None = None,
    files_dir: Path | None = None,
    scoring_config: ScoringConfig | None = None,
) -> AuditResult:
    """Built-in rules, plus IDS checks when `ids_path` is given (needs `files_dir`, where the IFC lives)."""
    snap = load_snapshot(engine, revision_id)
    with engine.connect() as conn:
        model_id = repo.model_id_for_revision(conn, revision_id)
    out, ids_hash = _with_ids(run_rules(snap, model_id), snap.meta.file_sha256, model_id, ids_path, files_dir)
    cfg = scoring_config or load_config()
    mhi = compute_mhi(out.counts, out.findings, cfg)
    repro = {
        "file_sha256": snap.meta.file_sha256,
        "ruleset_version": out.ruleset_version,
        "ids_hash": ids_hash,
        "engine_version": __version__,
        "scoring_config": cfg.version,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    summary = {
        "counts": out.counts,
        "rules": [vars(m) for m in out.rules],
        "reproducibility": repro,
        "mhi": asdict(mhi),
    }
    row = {
        "ruleset_version": out.ruleset_version,
        "ids_hash": ids_hash,
        "engine_version": __version__,
        "status": "completed",
        "summary_json": summary,
        "scoring_config_json": cfg.model_dump(),
    }
    with engine.begin() as conn:
        run = repo.insert_audit_run(conn, revision_id, row, out.findings)
    log.info("audit %s: %d findings on revision %s", run.id, len(out.findings), revision_id)
    return AuditResult(run.id, revision_id, out.findings, out.counts, repro, mhi)


def _with_ids(
    out: AuditOutput, ifc_sha: str, model_id: int, ids_path: Path | None, files_dir: Path | None
) -> tuple[AuditOutput, str | None]:
    if ids_path is None:
        return out, None
    if files_dir is None:
        raise ValueError("files_dir is required to run IDS checks")
    ids_hash = file_sha256(Path(ids_path))
    checked = _merge(out, run_ids(files_dir / f"{ifc_sha}.ifc", ids_path, model_id))
    store_file(Path(ids_path), files_dir, ids_hash, ".ids")
    return checked, ids_hash


def _merge(rules: AuditOutput, checks: AuditOutput) -> AuditOutput:
    """IDS results join rule results; ruleset_version keeps identifying the built-in rules only."""
    return AuditOutput(
        rules.findings + checks.findings,
        {**rules.counts, **checks.counts},
        rules.ruleset_version,
        rules.rules + checks.rules,
    )


def load_findings(engine: Engine, audit_run_id: int) -> tuple[Finding, ...]:
    with engine.connect() as conn:
        return repo.load_findings(conn, audit_run_id)


def load_audit_summary(engine: Engine, audit_run_id: int) -> dict:
    """summary_json (counts, rules, reproducibility, mhi) plus the scoring config the run used."""
    with engine.connect() as conn:
        return repo.load_audit_summary(conn, audit_run_id)
