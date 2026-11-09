"""Upload intake: validate, hash, content-address, enqueue. No IFC parsing here (D-06, D-18)."""

from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import Engine

from axiom.config import Settings
from axiom.ids import load_ids
from axiom.services import browse, jobs

IFC_MAGIC = b"ISO-10303-21;"
CHUNK = 1024 * 1024
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class TooLargeError(ValueError):
    pass


def accept_revision(
    engine: Engine,
    settings: Settings,
    model_id: int,
    src: BinaryIO,
    filename: str,
    *,
    ids_hash: str | None = None,
    geometry: bool = False,
    kinds: dict[str, str] = jobs.KINDS,
) -> int:
    """Validate + store an IFC upload and enqueue the pipeline job. Returns the job id."""
    browse.require_model(engine, model_id)
    if ids_hash is not None and not (
        SHA256.match(ids_hash) and (settings.files_dir / f"{ids_hash}.ids").exists()
    ):
        raise ValueError("unknown ids_hash; upload the IDS file first")
    tmp, sha = _receive(src, filename, ".ifc", settings)
    try:
        if not _has_step_header(tmp):
            raise ValueError("not an IFC file: missing the ISO-10303-21 header")
        _commit(tmp, settings.files_dir / f"{sha}.ifc")
    finally:
        tmp.unlink(missing_ok=True)
    payload = {"model_id": model_id, "file_sha256": sha, "ids_hash": ids_hash, "geometry": geometry}
    return jobs.enqueue(engine, "pipeline", payload, kinds=kinds)


def accept_ids(settings: Settings, src: BinaryIO, filename: str) -> str:
    """Validate an IDS file against the IDS 1.0 XSD and store it. Returns its sha256 (the ids_hash)."""
    tmp, sha = _receive(src, filename, ".ids", settings)
    try:
        try:
            load_ids(tmp)
        except (ValueError, SyntaxError) as e:  # SyntaxError covers xml ParseError
            raise ValueError(f"invalid IDS file {filename}: does not match the IDS 1.0 XSD") from e
        _commit(tmp, settings.files_dir / f"{sha}.ids")
    finally:
        tmp.unlink(missing_ok=True)
    return sha


def _receive(src: BinaryIO, filename: str, suffix: str, settings: Settings) -> tuple[Path, str]:
    if not filename.lower().endswith(suffix):
        raise ValueError(f"expected a {suffix} file")
    limit = settings.max_upload_mb * 1024 * 1024
    settings.files_dir.mkdir(parents=True, exist_ok=True)
    tmp = settings.files_dir / f".upload-{uuid.uuid4().hex}.part"
    digest, size = hashlib.sha256(), 0
    try:
        with tmp.open("wb") as out:
            while chunk := src.read(CHUNK):
                size += len(chunk)
                if size > limit:
                    raise TooLargeError(f"file exceeds the {settings.max_upload_mb} MB upload limit")
                digest.update(chunk)
                out.write(chunk)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return tmp, digest.hexdigest()


def _has_step_header(path: Path) -> bool:
    with path.open("rb") as fh:
        head = fh.read(64).lstrip(b"\xef\xbb\xbf \t\r\n")
    return head.startswith(IFC_MAGIC)


def _commit(tmp: Path, dest: Path) -> None:
    if not dest.exists():
        tmp.replace(dest)  # atomic rename within files_dir
