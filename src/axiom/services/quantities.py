"""Quantity reports and revision deltas for stored revisions (P07, D-17)."""

from __future__ import annotations

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
    """Qto totals per group; with `geometry`, geometry volumes as separate `method=geometry` rows."""
    snap = load_snapshot(engine, revision_id)
    return aggregate(snap, by, volumes_for(snap.meta.file_sha256, files_dir) if geometry else None)


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
    return geometry_volumes(files_dir / f"{file_sha256}.ifc")
