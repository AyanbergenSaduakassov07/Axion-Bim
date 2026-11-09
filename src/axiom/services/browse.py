"""Read-only views for the API (P08). Raises LookupError for missing ids."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, Row

from axiom.extract.snapshot import Element
from axiom.findings import Finding
from axiom.repo import audits as audit_repo
from axiom.repo import browse as repo
from axiom.repo import comparisons as cmp_repo
from axiom.repo import revisions as rev_repo
from axiom.revision import FindingEvent

FINDING_FILTERS = {"status": "status", "severity": "severity", "category": "category", "rule": "rule_id"}


def _found(row: Row | None, what: str, key: object) -> Row:
    if row is None:
        raise LookupError(f"{what} {key} not found")
    return row


def list_projects(engine: Engine) -> list[dict]:
    with engine.connect() as conn:
        return [r._asdict() for r in repo.list_projects(conn)]


def list_models(engine: Engine, project_id: int) -> list[dict]:
    with engine.connect() as conn:
        _found(repo.get_project(conn, project_id), "project", project_id)
        return [r._asdict() for r in repo.list_models(conn, project_id)]


def require_model(engine: Engine, model_id: int) -> None:
    with engine.connect() as conn:
        _found(repo.get_model(conn, model_id), "model", model_id)


def list_revisions(engine: Engine, model_id: int) -> list[dict]:
    with engine.connect() as conn:
        _found(repo.get_model(conn, model_id), "model", model_id)
        return [r._asdict() for r in repo.list_revisions(conn, model_id)]


def revision_summary(engine: Engine, revision_id: int) -> dict:
    with engine.connect() as conn:
        rev = _found(repo.get_revision(conn, revision_id), "revision", revision_id)
        latest = cmp_repo.latest_audit(conn, revision_id)
        return {
            **{c: getattr(rev, c) for c in ("id", "model_id", "seq", "file_sha256", "file_size", "status")},
            "schema_name": rev.schema_name,
            "metadata": rev.metadata_json,
            "class_counts": repo.class_counts(conn, revision_id),
            "latest_audit_id": latest.id if latest else None,
        }


def elements_page(engine: Engine, revision_id: int, filters: dict, limit: int, offset: int) -> dict:
    with engine.connect() as conn:
        _found(repo.get_revision(conn, revision_id), "revision", revision_id)
        total, rows = repo.elements_page(conn, revision_id, filters, limit, offset)
    return {"total": total, "limit": limit, "offset": offset, "items": [r._asdict() for r in rows]}


def revision_file(engine: Engine, files_dir: Path, revision_id: int) -> Path:
    with engine.connect() as conn:
        rev = _found(repo.get_revision(conn, revision_id), "revision", revision_id)
    path = files_dir / f"{rev.file_sha256}.ifc"
    if not path.is_file():
        raise LookupError(f"stored file for revision {revision_id} not found")
    return path


def spatial_tree(engine: Engine, revision_id: int) -> dict:
    with engine.connect() as conn:
        _found(repo.get_revision(conn, revision_id), "revision", revision_id)
        nodes, els = repo.spatial_tree(conn, revision_id)
    return {"nodes": [r._asdict() for r in nodes], "elements": [r._asdict() for r in els]}


def get_element(engine: Engine, revision_id: int, global_id: str) -> Element:
    with engine.connect() as conn:
        return _found(rev_repo.load_element(conn, revision_id, global_id), "element", global_id)


def list_audits(engine: Engine, revision_id: int) -> list[dict]:
    with engine.connect() as conn:
        _found(repo.get_revision(conn, revision_id), "revision", revision_id)
        return [_audit_row(r) for r in repo.list_audits(conn, revision_id)]


def _audit_row(r: Row) -> dict:
    mhi = r.summary_json["mhi"]
    return {
        **{c: getattr(r, c) for c in ("id", "revision_id", "ruleset_version", "ids_hash", "status")},
        "engine_version": r.engine_version,
        "created_at": r.created_at,
        "score": mhi["score"],
        "coverage": mhi["coverage"],
        "blocked": mhi["blocked"],
    }


def audit_summary(engine: Engine, audit_run_id: int) -> dict:
    with engine.connect() as conn:
        _found(repo.get_audit(conn, audit_run_id), "audit", audit_run_id)
        return audit_repo.load_audit_summary(conn, audit_run_id)


def findings(engine: Engine, audit_run_id: int, filters: dict[str, str | None]) -> list[Finding]:
    with engine.connect() as conn:
        _found(repo.get_audit(conn, audit_run_id), "audit", audit_run_id)
        items = audit_repo.load_findings(conn, audit_run_id)
    wanted = {FINDING_FILTERS[k]: v for k, v in filters.items() if v}
    return [f for f in items if all(str(getattr(f, k)) == v for k, v in wanted.items())]


def health_index(engine: Engine, audit_run_id: int) -> dict:
    return audit_summary(engine, audit_run_id)["mhi"]


def list_comparisons(engine: Engine, revision_id: int) -> list[dict]:
    with engine.connect() as conn:
        _found(repo.get_revision(conn, revision_id), "revision", revision_id)
        return [r._asdict() for r in repo.list_comparisons(conn, revision_id)]


def comparison(engine: Engine, comparison_id: int) -> dict:
    with engine.connect() as conn:
        return _found(repo.get_comparison(conn, comparison_id), "comparison", comparison_id)._asdict()


def changes(engine: Engine, comparison_id: int) -> list[dict]:
    with engine.connect() as conn:
        _found(repo.get_comparison(conn, comparison_id), "comparison", comparison_id)
        return [
            {**r._asdict(), "old": r.old_json, "new": r.new_json}
            for r in repo.list_changes(conn, comparison_id)
        ]


def events(engine: Engine, comparison_id: int) -> tuple[FindingEvent, ...]:
    with engine.connect() as conn:
        _found(repo.get_comparison(conn, comparison_id), "comparison", comparison_id)
        return cmp_repo.load_events(conn, comparison_id)
