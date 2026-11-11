"""Project IDS library (D-34): requirement files kept per project so every upload can reuse them."""

from __future__ import annotations

from typing import BinaryIO

from sqlalchemy import Engine

from axiom.config import Settings
from axiom.ids import load_ids
from axiom.ids.diff import diff_ids
from axiom.repo import browse as browse_repo
from axiom.repo import ids_library as repo
from axiom.services.uploads import accept_ids


def _project(conn, project_id: int) -> None:
    if browse_repo.get_project(conn, project_id) is None:
        raise LookupError(f"project {project_id} not found")


def list_entries(engine: Engine, project_id: int) -> list[dict]:
    with engine.connect() as conn:
        _project(conn, project_id)
        return [r._asdict() for r in repo.list_entries(conn, project_id)]


def add(
    engine: Engine, settings: Settings, project_id: int, src: BinaryIO, *, filename: str, name: str
) -> dict:
    """Validates and stores the file; the same file again returns the existing entry. First is default."""
    with engine.connect() as conn:
        _project(conn, project_id)
    ids_hash = accept_ids(settings, src, filename)  # raises ValueError on an invalid IDS
    with engine.begin() as conn:
        if (row := repo.find(conn, project_id, ids_hash=ids_hash)) is None:
            first = not repo.list_entries(conn, project_id)
            repo.insert_entry(conn, project_id, name.strip() or filename or ids_hash[:12], ids_hash, first)
            row = repo.find(conn, project_id, ids_hash=ids_hash)
        return row._asdict()


def _entry(conn, project_id: int, entry_id: int) -> None:
    _project(conn, project_id)
    if repo.find(conn, project_id, entry_id=entry_id) is None:
        raise LookupError(f"IDS entry {entry_id} not found in project {project_id}")


def set_default(engine: Engine, project_id: int, entry_id: int, is_default: bool) -> list[dict]:
    with engine.begin() as conn:
        _entry(conn, project_id, entry_id)
        repo.set_default(conn, project_id, entry_id, is_default)
        return [r._asdict() for r in repo.list_entries(conn, project_id)]


def rename(engine: Engine, project_id: int, entry_id: int, name: str) -> dict:
    name = name.strip()
    if not name:
        raise ValueError("name must not be blank")
    with engine.begin() as conn:
        _entry(conn, project_id, entry_id)
        repo.rename(conn, entry_id, name)
        return repo.find(conn, project_id, entry_id=entry_id)._asdict()


def remove(engine: Engine, project_id: int, entry_id: int) -> None:
    """Removes the library entry only: the stored file stays, because past audits cite its hash."""
    with engine.begin() as conn:
        _entry(conn, project_id, entry_id)
        repo.delete_entry(conn, entry_id)


def diff(engine: Engine, settings: Settings, project_id: int, entry_id: int, against_id: int) -> dict:
    """Specification changes from entry `against_id` (older) to `entry_id` (newer)."""
    with engine.connect() as conn:
        _project(conn, project_id)
        rows = [repo.find(conn, project_id, entry_id=i) for i in (against_id, entry_id)]
    if None in rows:
        raise LookupError(f"IDS entry not found in project {project_id}")
    old, new = (load_ids(settings.files_dir / f"{r.ids_hash}.ids") for r in rows)
    return {"base": rows[0].name, "head": rows[1].name, **diff_ids(old, new)}
