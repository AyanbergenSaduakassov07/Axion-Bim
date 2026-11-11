"""Issue triage rows."""

from __future__ import annotations

from sqlalchemy import Connection, Row, func, select
from sqlalchemy.dialects.sqlite import insert

from axiom.repo.tables import issue_events, issues

COLUMNS = (
    issues.c.identity_key,
    issues.c.state,
    issues.c.assignee,
    issues.c.due_date,
    issues.c.note,
    issues.c.updated_at,
)


def list_issues(conn: Connection, model_id: int) -> list[Row]:
    return list(conn.execute(select(*COLUMNS).where(issues.c.model_id == model_id).order_by(issues.c.id)))


def upsert(conn: Connection, model_id: int, keys: list[str], fields: dict) -> None:
    """Insert missing rows as `open`; on existing rows overwrite only `fields`."""
    rows = [{"model_id": model_id, "identity_key": k, "state": "open"} | fields for k in keys]
    stmt = insert(issues).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[issues.c.model_id, issues.c.identity_key],
        set_={**{k: stmt.excluded[k] for k in fields}, "updated_at": func.now()},
    )
    conn.execute(stmt)


def current(conn: Connection, model_id: int, keys: list[str]) -> dict[str, Row]:
    q = select(*COLUMNS).where(issues.c.model_id == model_id, issues.c.identity_key.in_(keys))
    return {r.identity_key: r for r in conn.execute(q)}


def insert_events(conn: Connection, rows: list[dict]) -> None:
    if rows:
        conn.execute(insert(issue_events), rows)


def history(conn: Connection, model_id: int, identity_key: str) -> list[Row]:
    e = issue_events.c
    q = select(e.field, e.old, e.new, e.author, e.at).where(
        e.model_id == model_id, e.identity_key == identity_key
    )
    return list(conn.execute(q.order_by(e.id)))
