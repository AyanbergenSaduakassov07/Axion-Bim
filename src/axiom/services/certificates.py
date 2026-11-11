"""Issue and read frozen acceptance certificates (D-42). The live gate stays in services/gate.py."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Connection, Engine

from axiom.certificate import digest, verify
from axiom.repo import audits as audit_repo
from axiom.repo import browse as repo
from axiom.repo import certificates as cert_repo
from axiom.services import gate


def _audit(conn: Connection, audit_run_id: int):
    audit = repo.get_audit(conn, audit_run_id)
    if audit is None:
        raise LookupError(f"audit {audit_run_id} not found")
    return audit


def _payload(conn: Connection, audit, issued_by: str) -> dict:
    rev = repo.get_revision(conn, audit.revision_id)
    model = repo.get_model(conn, rev.model_id)
    summary = audit_repo.load_audit_summary(conn, audit.id)
    repro = summary["reproducibility"]
    return {
        **gate.for_audit(conn, audit),  # decision, reasons, policy
        "score": summary["mhi"]["score"],
        "project": repo.get_project(conn, model.project_id).name,
        "model": model.name,
        "revision_seq": rev.seq,
        "audit_run_id": audit.id,
        "file_sha256": repro["file_sha256"],
        "ruleset_version": repro["ruleset_version"],
        "ids_hash": repro["ids_hash"],
        "engine_version": repro["engine_version"],
        "scoring_config": repro["scoring_config"],
        "audited_at": repro["created_at"],
        "issued_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "issued_by": issued_by,
    }


def _out(row) -> dict:
    return {**row._asdict(), "payload": row.payload_json, "valid": verify(row.payload_json, row.sha256)}


def issue(engine: Engine, audit_run_id: int, issued_by: str) -> dict:
    with engine.begin() as conn:
        payload = _payload(conn, _audit(conn, audit_run_id), issued_by)
        cid = cert_repo.insert_certificate(conn, audit_run_id, payload, digest(payload))
        return next(_out(r) for r in cert_repo.list_for_audit(conn, audit_run_id) if r.id == cid)


def list_for_audit(engine: Engine, audit_run_id: int) -> list[dict]:
    with engine.connect() as conn:
        _audit(conn, audit_run_id)
        return [_out(r) for r in cert_repo.list_for_audit(conn, audit_run_id)]
