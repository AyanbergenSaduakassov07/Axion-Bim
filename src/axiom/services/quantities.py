"""Quantity reports and revision deltas for stored revisions (P07, D-17)."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import Engine

from axiom.quantities import QuantityDelta, QuantityRow, aggregate, geometry_volumes, quantity_delta
from axiom.services.revisions import load_snapshot


def report(
    engine: Engine,
    revision_id: int,
    by: str = "class",
    *,
    geometry: bool = False,
    files_dir: Path | None = None,
) -> tuple[QuantityRow, ...]:
    """Qto totals per group, plus `method=geometry` rows when volumes are known: computed now with
    `geometry`, else whatever a geometry audit cached (the API never runs IFC processing itself)."""
    snap = load_snapshot(engine, revision_id)
    sha = snap.meta.file_sha256
    volumes = volumes_for(sha, files_dir) if geometry else cached_volumes(sha, files_dir)
    return aggregate(snap, by, volumes)


def delta(
    engine: Engine,
    base: int,
    head: int,
    by: str = "class",
    *,
    geometry: bool = False,
    files_dir: Path | None = None,
) -> tuple[QuantityDelta, ...]:
    return quantity_delta(
        report(engine, base, by, geometry=geometry, files_dir=files_dir),
        report(engine, head, by, geometry=geometry, files_dir=files_dir),
    )


def volumes_for(file_sha256: str, files_dir: Path | None) -> dict[int, float]:
    if files_dir is None:
        raise ValueError("files_dir is required for geometry quantities")
    volumes = geometry_volumes(files_dir / f"{file_sha256}.ifc")
    _cache_path(file_sha256, files_dir).write_text(json.dumps(volumes))
    return volumes


def cached_volumes(file_sha256: str, files_dir: Path | None) -> dict[int, float] | None:
    path = _cache_path(file_sha256, files_dir) if files_dir else None
    if path is None or not path.exists():
        return None
    return {int(k): v for k, v in json.loads(path.read_text()).items()}


def _cache_path(file_sha256: str, files_dir: Path) -> Path:
    return files_dir / f"{file_sha256}.volumes.json"  # content-addressed like the IFC, so never stale
