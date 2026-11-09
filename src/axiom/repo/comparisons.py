"""Comparison, change and finding-event rows."""

from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import Connection, Row, insert, select

from axiom.repo.tables import audit_runs, comparisons, finding_events, revision_changes, revisions
from axiom.revision import Change, FindingEvent


def revision_row(conn: Connection, revision_id: int) -> Row:
    return conn.execute(select(revisions).where(revisions.c.id == revision_id)).one()


def previous_revision_id(conn: Connection, model_id: int, seq: int) -> int | None:
    q = (
        select(revisions.c.id)
        .where(revisions.c.model_id == model_id, revisions.c.seq < seq)
        .order_by(revisions.c.seq.desc())
        .limit(1)
    )
    return conn.execute(q).scalar()


def latest_audit(conn: Connection, revision_id: int) -> Row | None:
    q = select(audit_runs).where(audit_runs.c.revision_id == revision_id).order_by(audit_runs.c.id.desc())
    return conn.execute(q.limit(1)).first()


def audited_revisions(conn: Connection, model_id: int, max_seq: int) -> list[int]:
    """Revisions up to max_seq that have at least one audit, oldest first."""
    q = (
        select(revisions.c.id)
        .where(revisions.c.model_id == model_id, revisions.c.seq <= max_seq)
        .where(revisions.c.id.in_(select(audit_runs.c.revision_id)))
        .order_by(revisions.c.seq)
    )
    return list(conn.execute(q).scalars())


def insert_comparison(
    conn: Connection, row: dict, changes: tuple[Change, ...], events: tuple[FindingEvent, ...]
) -> int:
    cid = conn.execute(insert(comparisons).returning(comparisons.c.id), row).scalar_one()
    if changes:
        conn.execute(
            insert(revision_changes),
            [
                {
                    "comparison_id": cid,
                    "kind": c.kind,
                    "global_id": c.global_id,
                    "ifc_class": c.ifc_class,
                    "path": c.path,
                    "old_json": c.old,
                    "new_json": c.new,
                }  # fmt: skip
                for c in changes
            ],
        )
    if events:
        conn.execute(insert(finding_events), [{"comparison_id": cid, **asdict(e)} for e in events])
    return cid


def load_events(conn: Connection, comparison_id: int) -> tuple[FindingEvent, ...]:
    cols = [finding_events.c[f] for f in FindingEvent.__dataclass_fields__]
    q = select(*cols).where(finding_events.c.comparison_id == comparison_id).order_by(finding_events.c.id)
    return tuple(FindingEvent(**r) for r in conn.execute(q).mappings())
