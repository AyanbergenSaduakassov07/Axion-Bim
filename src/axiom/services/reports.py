"""Assemble the canonical audit report from stored results (no IFC processing). Raises LookupError."""

from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import Connection, Engine

from axiom.repo import audits as audit_repo
from axiom.repo import browse as repo
from axiom.repo import comparisons as cmp_repo
from axiom.repo import issues as issue_repo
from axiom.report import FORMAT_VERSION, render  # noqa: F401  (render re-exported for callers)
from axiom.services import gate
from axiom.services.issues import EDITABLE

REVISION_META = ("project_name", "authoring_app")


def build(engine: Engine, audit_run_id: int, comparison_id: int | None = None) -> dict:
    """Audit + MHI + reproducibility, plus the comparison headed by this audit (latest, or the given one)."""
    with engine.connect() as conn:
        audit = repo.get_audit(conn, audit_run_id)
        if audit is None:
            raise LookupError(f"audit {audit_run_id} not found")
        summary = audit_repo.load_audit_summary(conn, audit_run_id)
        cmp = (
            repo.get_comparison(conn, comparison_id)
            if comparison_id
            else repo.latest_comparison_for_audit(conn, audit_run_id)
        )
        if comparison_id and (cmp is None or cmp.head_audit_run_id != audit_run_id):
            raise LookupError(f"comparison {comparison_id} not found for audit {audit_run_id}")
        return {
            "format": FORMAT_VERSION,
            "audit": {
                "id": audit.id,
                "status": audit.status,
                "revision": _revision(conn, audit.revision_id),
            },
            "reproducibility": summary["reproducibility"],
            "mhi": summary["mhi"],
            "gate": gate.for_audit(conn, audit),
            "counts": summary["counts"],
            "rules": summary["rules"],
            "findings": _findings(conn, audit_run_id, audit.revision_id),
            "comparison": _comparison(conn, cmp) if cmp else None,
        }


def _findings(conn: Connection, audit_run_id: int, revision_id: int) -> list[dict]:
    locators = repo.element_locators(conn, revision_id)  # for BCF viewpoints
    model_id = repo.get_revision(conn, revision_id).model_id
    triage = {
        i.identity_key: {k: getattr(i, k) for k in EDITABLE} for i in issue_repo.list_issues(conn, model_id)
    }
    history = issue_repo.history_by_key(conn, model_id)
    return [
        {
            **f.model_dump(),
            "origin_m": locators.get(f.step_id, (None, None))[0],
            "authoring_tool_id": locators.get(f.step_id, (None, None))[1],
            "issue": triage.get(f.identity_key),
            "history": history.get(f.identity_key, []),
        }
        for f in audit_repo.load_findings(conn, audit_run_id)
    ]


def _revision(conn: Connection, revision_id: int) -> dict:
    rev = repo.get_revision(conn, revision_id)
    meta = rev.metadata_json or {}
    return {
        "id": rev.id,
        "seq": rev.seq,
        "file_sha256": rev.file_sha256,
        "schema_name": rev.schema_name,
        **{k: meta.get(k) for k in REVISION_META},
    }


def _comparison(conn: Connection, cmp) -> dict:
    return {
        "id": cmp.id,
        "base": _revision(conn, cmp.base_revision_id),
        "head": _revision(conn, cmp.head_revision_id),
        "identity_unstable": cmp.identity_unstable,
        "summary": cmp.summary_json,
        "changes": [
            {
                "kind": r.kind,
                "global_id": r.global_id,
                "ifc_class": r.ifc_class,
                "path": r.path,
                "old": r.old_json,
                "new": r.new_json,
            }
            for r in repo.list_changes(conn, cmp.id)
        ],  # fmt: skip
        "events": [asdict(e) for e in cmp_repo.load_events(conn, cmp.id)],
    }
