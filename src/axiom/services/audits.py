"""Audit a stored revision: rules -> findings + per-rule counts, persisted with a reproducibility block."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Engine

from axiom import __version__
from axiom.findings import Finding
from axiom.repo import audits as repo
from axiom.rules import run_rules
from axiom.services.revisions import load_snapshot

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuditResult:
    audit_run_id: int
    revision_id: int
    findings: tuple[Finding, ...]
    counts: dict[str, dict[str, int]]
    reproducibility: dict


def run_audit(engine: Engine, revision_id: int) -> AuditResult:
    snap = load_snapshot(engine, revision_id)
    with engine.connect() as conn:
        model_id = repo.model_id_for_revision(conn, revision_id)
    out = run_rules(snap, model_id)
    repro = {
        "file_sha256": snap.meta.file_sha256,
        "ruleset_version": out.ruleset_version,
        "ids_hash": None,
        "engine_version": __version__,
        "scoring_config": None,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    summary = {"counts": out.counts, "rules": [vars(m) for m in out.rules], "reproducibility": repro}
    row = {
        "ruleset_version": out.ruleset_version,
        "ids_hash": None,
        "engine_version": __version__,
        "status": "completed",
        "summary_json": summary,
    }
    with engine.begin() as conn:
        run = repo.insert_audit_run(conn, revision_id, row, out.findings)
    log.info("audit %s: %d findings on revision %s", run.id, len(out.findings), revision_id)
    return AuditResult(run.id, revision_id, out.findings, out.counts, repro)


def load_findings(engine: Engine, audit_run_id: int) -> tuple[Finding, ...]:
    with engine.connect() as conn:
        return repo.load_findings(conn, audit_run_id)
