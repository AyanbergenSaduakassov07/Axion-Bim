"""Acceptance gate for an audit: stored findings + current issue triage + the project's policy (D-36).

Computed at read time, so a waiver or a policy change shows at once and no IFC is touched.
"""

from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import Connection, Engine

from axiom.repo import audits as audit_repo
from axiom.repo import browse as repo
from axiom.repo import issues as issue_repo
from axiom.repo import projects as project_repo
from axiom.score.gate import GatePolicy, decide

WAIVED_STATE = "accepted"  # issue state meaning "the reviewer takes this finding as it is"


def _policy(project) -> GatePolicy:
    return GatePolicy(project.gate_min_score, project.gate_block_severity, project.gate_require_ids)


def _effective(conn: Connection, project, stage: str | None) -> GatePolicy:
    """The stage's own policy when one is stored, else the project default (D-45)."""
    return _policy((stage and project_repo.stage_policy(conn, project.id, stage)) or project)


def for_audit(conn: Connection, audit) -> dict:
    rev = repo.get_revision(conn, audit.revision_id)
    model = repo.get_model(conn, rev.model_id)
    policy = _effective(conn, repo.get_project(conn, model.project_id), rev.stage)
    waived = {i.identity_key for i in issue_repo.list_issues(conn, model.id) if i.state == WAIVED_STATE}
    findings = [(f.severity, f.status, f.identity_key) for f in audit_repo.load_findings(conn, audit.id)]
    score = audit_repo.load_audit_summary(conn, audit.id)["mhi"]["score"]
    result = decide(score, findings, waived=waived, ids_checked=audit.ids_hash is not None, policy=policy)
    return {**result, "policy": asdict(policy), "stage": rev.stage}


def audit_gate(engine: Engine, audit_run_id: int) -> dict:
    with engine.connect() as conn:
        audit = repo.get_audit(conn, audit_run_id)
        if audit is None:
            raise LookupError(f"audit {audit_run_id} not found")
        return for_audit(conn, audit)


def get_policy(engine: Engine, project_id: int, stage: str | None = None) -> dict:
    with engine.connect() as conn:
        project = repo.get_project(conn, project_id)
        if project is None:
            raise LookupError(f"project {project_id} not found")
        return asdict(_effective(conn, project, stage))


def set_policy(engine: Engine, project_id: int, policy: GatePolicy, stage: str | None = None) -> dict:
    values = {f"gate_{k}": v for k, v in asdict(policy).items()}
    with engine.begin() as conn:
        if repo.get_project(conn, project_id) is None:
            raise LookupError(f"project {project_id} not found")
        if stage:
            project_repo.set_stage_policy(conn, project_id, stage, values)
        else:
            project_repo.set_gate_policy(conn, project_id, values)
    return asdict(policy)


def set_stage(engine: Engine, revision_id: int, stage: str | None) -> dict:
    with engine.begin() as conn:
        if repo.get_revision(conn, revision_id) is None:
            raise LookupError(f"revision {revision_id} not found")
        project_repo.set_revision_stage(conn, revision_id, stage)
        return repo.get_revision(conn, revision_id)._asdict()
