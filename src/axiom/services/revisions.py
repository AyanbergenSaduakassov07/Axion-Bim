"""Revision ingest: hash -> content-addressed store -> extract -> persist. Idempotent per file hash."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine

from axiom.extract import extract, file_sha256
from axiom.extract.snapshot import Snapshot
from axiom.repo import revisions as repo

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestResult:
    revision_id: int
    seq: int
    file_sha256: str
    created: bool


def store_file(path: Path, files_dir: Path, sha256: str, suffix: str = ".ifc") -> Path:
    """Content-addressed copy: files_dir/<sha256><suffix>."""
    dest = files_dir / f"{sha256}{suffix}"
    if not dest.exists():
        files_dir.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".part")
        shutil.copyfile(path, tmp)
        tmp.replace(dest)  # atomic: a crash never leaves a truncated file under the final name
    return dest


def ingest(engine: Engine, model_id: int, path: str | Path, *, files_dir: Path) -> IngestResult:
    path = Path(path)
    sha = file_sha256(path)
    with engine.connect() as conn:
        existing = repo.find_by_hash(conn, model_id, sha)
    if existing is not None:
        log.info("revision %s already ingested (sha %s)", existing.id, sha[:12])
        return IngestResult(existing.id, existing.seq, sha, created=False)
    stored = store_file(path, files_dir, sha)
    snap = extract(stored)  # extract outside the transaction: it can take seconds on large models
    with engine.begin() as conn:
        rev = repo.insert_snapshot(conn, model_id, snap)
    return IngestResult(rev.id, rev.seq, sha, created=True)


def load_snapshot(engine: Engine, revision_id: int) -> Snapshot:
    with engine.connect() as conn:
        return repo.load_snapshot(conn, revision_id)
