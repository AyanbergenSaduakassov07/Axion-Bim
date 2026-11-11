"""Issue workflow on findings (D-32): who fixes what, by when, and whether it is accepted or disputed."""

from __future__ import annotations

from datetime import date

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


def _text(v: object) -> str | None:
    return None if v is None else v.isoformat() if isinstance(v, date) else str(v)


def _events(model_id: int, before: dict, keys: list[str], fields: dict, author: str | None) -> list[dict]:
    rows = []
    for k in keys:
        old_row = before.get(k)
        for field in EDITABLE:
            if field not in fields:
                continue
            old = _text(getattr(old_row, field)) if old_row else ("open" if field == "state" else None)
            new = _text(fields[field])
            if old != new:
                rows.append(
                    {
                        "model_id": model_id,
                        "identity_key": k,
                        "field": field,
                        "old": old,
                        "new": new,
                        "author": author,
                    }
                )
    return rows


def history(engine: Engine, model_id: int, identity_key: str) -> list[dict]:
    with engine.connect() as conn:
        _model(conn, model_id)
        return [r._asdict() for r in repo.history(conn, model_id, identity_key)]


def update(engine: Engine, model_id: int, keys: list[str], fields: dict, author: str | None = None) -> int:
    unknown = set(fields) - set(EDITABLE)
    if unknown:
        raise ValueError(f"not editable: {sorted(unknown)}")
    keys = list(dict.fromkeys(keys))
    with engine.begin() as conn:
        _model(conn, model_id)
        for i in range(0, len(keys), BATCH):
            batch = keys[i : i + BATCH]
            events = _events(model_id, repo.current(conn, model_id, batch), batch, fields, author)
            repo.upsert(conn, model_id, batch, fields)
            repo.insert_events(conn, events)
    return len(keys)
