"""Audit run + finding rows."""

from __future__ import annotations

from sqlalchemy import Connection, Row, insert, select

from axiom.findings import Finding
from axiom.repo.tables import audit_runs, findings, revisions


def model_id_for_revision(conn: Connection, revision_id: int) -> int:
    return conn.execute(select(revisions.c.model_id).where(revisions.c.id == revision_id)).scalar_one()


def insert_audit_run(conn: Connection, revision_id: int, row: dict, items: tuple[Finding, ...]) -> Row:
    run = conn.execute(insert(audit_runs).returning(audit_runs), {"revision_id": revision_id, **row}).one()
    if items:
        conn.execute(insert(findings), [_finding_row(run.id, f) for f in items])
    return run


def _finding_row(run_id: int, f: Finding) -> dict:
    data = f.model_dump()
    return {"audit_run_id": run_id, "evidence_json": data.pop("evidence"), **data}


def load_findings(conn: Connection, audit_run_id: int) -> tuple[Finding, ...]:
    rows = conn.execute(
        select(findings).where(findings.c.audit_run_id == audit_run_id).order_by(findings.c.id)
    ).mappings()
    return tuple(
        Finding(evidence=r["evidence_json"], **{k: r[k] for k in Finding.model_fields if k != "evidence"})
        for r in rows
    )


def load_audit_summary(conn: Connection, audit_run_id: int) -> dict:
    row = conn.execute(
        select(audit_runs.c.summary_json, audit_runs.c.scoring_config_json).where(
            audit_runs.c.id == audit_run_id
        )
    ).one()
    return {**row.summary_json, "scoring_config": row.scoring_config_json}
