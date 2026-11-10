"""Project IDS library rows."""

from __future__ import annotations

from sqlalchemy import Connection, Row, insert, select, update

from axiom.repo.tables import project_ids

COLUMNS = (
    project_ids.c.id,
    project_ids.c.name,
    project_ids.c.ids_hash,
    project_ids.c.is_default,
    project_ids.c.created_at,
)


def list_entries(conn: Connection, project_id: int) -> list[Row]:
    q = select(*COLUMNS).where(project_ids.c.project_id == project_id).order_by(project_ids.c.id)
    return list(conn.execute(q))


def find(
    conn: Connection, project_id: int, *, entry_id: int | None = None, ids_hash: str | None = None
) -> Row | None:
    q = select(*COLUMNS).where(project_ids.c.project_id == project_id)
    q = (
        q.where(project_ids.c.id == entry_id)
        if entry_id is not None
        else q.where(project_ids.c.ids_hash == ids_hash)
    )
    return conn.execute(q).first()


def insert_entry(conn: Connection, project_id: int, name: str, ids_hash: str, is_default: bool) -> None:
    conn.execute(
        insert(project_ids),
        {"project_id": project_id, "name": name, "ids_hash": ids_hash, "is_default": is_default},
    )


def set_default(conn: Connection, project_id: int, entry_id: int, is_default: bool) -> None:
    """At most one default per project: setting one clears the others."""
    if is_default:
        conn.execute(
            update(project_ids).where(project_ids.c.project_id == project_id).values(is_default=False)
        )
    conn.execute(update(project_ids).where(project_ids.c.id == entry_id).values(is_default=is_default))
