"""Element volumes from tessellated geometry (opt-in; slower than reading Qto sets)."""

from __future__ import annotations

import logging
import multiprocessing
from collections.abc import Iterable
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.shape

log = logging.getLogger(__name__)


def geometry_volumes(ifc_path: Path, step_ids: Iterable[int] | None = None) -> dict[int, float]:
    """step_id -> volume in m3 (the iterator converts to SI). Elements that fail to tessellate are skipped."""
    f = ifcopenshell.open(str(ifc_path))
    include = [f.by_id(i) for i in step_ids] if step_ids is not None else f.by_type("IfcElement")
    if not include:
        return {}
    it = ifcopenshell.geom.iterator(
        ifcopenshell.geom.settings(), f, multiprocessing.cpu_count(), include=include
    )
    out: dict[int, float] = {}
    if not it.initialize():
        log.warning("geometry: nothing tessellated in %s", Path(ifc_path).name)
        return out
    while True:
        shape = it.get()
        out[shape.id] = ifcopenshell.util.shape.get_volume(shape.geometry)
        if not it.next():
            break
    log.info("geometry: %d/%d volumes from %s", len(out), len(include), Path(ifc_path).name)
    return out
