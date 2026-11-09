"""Job queue service: enqueue, inspect, and the runner's claim/finish steps (D-06, D-18)."""

from __future__ import annotations

from sqlalchemy import Engine, Row

from axiom.repo import jobs as repo

# kind -> "module:function" run in the job child; only these targets can ever be imported there
KINDS = {"pipeline": "axiom.jobs.kinds:pipeline", "compare": "axiom.jobs.kinds:compare"}


def enqueue(engine: Engine, kind: str, payload: dict, *, kinds: dict[str, str] = KINDS) -> int:
    if kind not in kinds:
        raise ValueError(f"unknown job kind {kind!r}")
    with engine.begin() as conn:
        return repo.insert_job(conn, kind, payload)


def get_job(engine: Engine, job_id: int) -> dict | None:
    with engine.connect() as conn:
        row = repo.get_job(conn, job_id)
    if row is None:
        return None
    return {
        "id": row.id,
        "kind": row.kind,
        "status": row.status,
        "progress": row.progress,
        "result": row.result_json,
        "error_message": row.error_message,
        "created_at": row.created_at,
        "started_at": row.started_at,
        "finished_at": row.finished_at,
    }


def claim_next(engine: Engine) -> Row | None:
    with engine.begin() as conn:
        return repo.claim_next(conn)


def finish(engine: Engine, job_id: int, *, result: dict | None = None, error: str | None = None) -> None:
    with engine.begin() as conn:
        repo.finish(conn, job_id, result=result, error=error)


def fail_orphans(engine: Engine) -> int:
    with engine.begin() as conn:
        return repo.fail_running(conn, "interrupted: the server restarted while this job was running")
