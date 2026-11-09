"""Job queue rows (D-06)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Connection, Row, insert, select, update

from axiom.repo.tables import jobs


def insert_job(conn: Connection, kind: str, payload: dict) -> int:
    row = {"kind": kind, "payload_json": payload, "status": "queued", "progress": 0.0}
    return conn.execute(insert(jobs).returning(jobs.c.id), row).scalar_one()


def get_job(conn: Connection, job_id: int) -> Row | None:
    return conn.execute(select(jobs).where(jobs.c.id == job_id)).first()


def claim_next(conn: Connection) -> Row | None:
    """Oldest queued job -> running. The status guard keeps a second claimer from taking it too."""
    job_id = conn.execute(
        select(jobs.c.id).where(jobs.c.status == "queued").order_by(jobs.c.id).limit(1)
    ).scalar()
    if job_id is None:
        return None
    claimed = conn.execute(
        update(jobs)
        .where(jobs.c.id == job_id, jobs.c.status == "queued")
        .values(status="running", started_at=datetime.now(UTC))
    )
    return get_job(conn, job_id) if claimed.rowcount == 1 else None


def finish(conn: Connection, job_id: int, *, result: dict | None, error: str | None) -> None:
    values = {"status": "error" if error else "done", "result_json": result, "error_message": error}
    if not error:
        values["progress"] = 1.0
    conn.execute(update(jobs).where(jobs.c.id == job_id).values(finished_at=datetime.now(UTC), **values))


def fail_running(conn: Connection, message: str) -> int:
    q = update(jobs).where(jobs.c.status == "running")
    return conn.execute(
        q.values(status="error", error_message=message, finished_at=datetime.now(UTC))
    ).rowcount
