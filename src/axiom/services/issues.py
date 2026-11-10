"""Issue workflow on findings (D-32): who fixes what, by when, and whether it is accepted or disputed."""

from __future__ import annotations

from sqlalchemy import Engine

from axiom.repo import browse as browse_repo
from axiom.repo import issues as repo

STATES = ("open", "in_progress", "disputed", "accepted", "closed")  # distinct from finding status/event words
EDITABLE = ("state", "assignee", "due_date", "note")
BATCH = 500  # rows per INSERT, under SQLite's bound-parameter limit


def _model(conn, model_id: int) -> None:
    if browse_repo.get_model(conn, model_id) is None:
        raise LookupError(f"model {model_id} not found")


def list_issues(engine: Engine, model_id: int) -> list[dict]:
    with engine.connect() as conn:
        _model(conn, model_id)
        return [r._asdict() for r in repo.list_issues(conn, model_id)]


def update(engine: Engine, model_id: int, keys: list[str], fields: dict) -> int:
    unknown = set(fields) - set(EDITABLE)
    if unknown:
        raise ValueError(f"not editable: {sorted(unknown)}")
    keys = list(dict.fromkeys(keys))
    with engine.begin() as conn:
        _model(conn, model_id)
        for i in range(0, len(keys), BATCH):
            repo.upsert(conn, model_id, keys[i : i + BATCH], fields)
    return len(keys)
