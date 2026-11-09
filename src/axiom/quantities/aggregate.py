"""Quantity take-off totals per group (P07). Pure over a Snapshot; geometry volumes are passed in.

Rows are keyed by (group, qto, quantity, method): a total never mixes Qto sets or methods (qto|geometry).
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal

from axiom.extract.snapshot import Element, Snapshot

Method = Literal["qto", "geometry"]
GEOMETRY_QTO = "(geometry)"
NONE = "(none)"
SI_UNITS = (("CUBIC_", "m3"), ("SQUARE_", "m2"))


@dataclass(frozen=True)
class QuantityRow:
    group: str
    qto: str
    quantity: str
    method: Method
    unit: str | None  # SI unit of `total`
    total: float
    count: int  # elements contributing
    missing: tuple[str, ...]  # GlobalIds in the group, of a class that carries this quantity, without a value


@dataclass(frozen=True)
class QuantityDelta:
    group: str
    qto: str
    quantity: str
    method: Method
    unit: str | None
    old: float | None
    new: float | None


def si_unit(raw: str | None) -> str | None:
    """si_value is already scaled to SI by the extractor; this only names the unit."""
    if raw is None:
        return None
    for prefix, unit in SI_UNITS:
        if raw.startswith(prefix):
            return unit
    if raw.endswith("METRE") or raw in {"FOOT", "INCH", "YARD", "MILE"}:
        return "m"
    return "kg" if raw.endswith("GRAM") or raw == "POUND" else raw


def _groupers(snap: Snapshot) -> dict[str, Callable[[Element], str]]:
    storeys = {n.global_id: n.name or n.global_id for n in snap.spatial}
    return {
        "class": lambda e: e.ifc_class,
        "storey": lambda e: storeys.get(e.storey_global_id or "", NONE),
        "material": lambda e: " + ".join(sorted({m.name for m in e.materials})) or NONE,
        "classification": lambda e: (
            ", ".join(sorted(f"{c.system or '?'}:{c.identification or '?'}" for c in e.classifications))
            or NONE
        ),
    }


GROUPS = ("class", "storey", "material", "classification")


def aggregate(
    snap: Snapshot, by: str = "class", geometry: Mapping[int, float] | None = None
) -> tuple[QuantityRow, ...]:
    """`geometry`: step_id -> volume (m3) from geometry_volumes(); reported as separate `geometry` rows."""
    if by not in GROUPS:
        raise ValueError(f"unknown grouping {by!r}; use one of {', '.join(GROUPS)}")
    group_of = _groupers(snap)[by]
    values: dict[tuple, dict[str, float]] = defaultdict(dict)  # key -> {global_id: si_value}
    units: dict[tuple, str | None] = {}
    for e in snap.elements:
        for q in e.quantities:
            key = (group_of(e), q.qto, q.name, q.method)
            values[key][e.global_id] = q.si_value
            units.setdefault(key, si_unit(q.unit))
        if geometry and e.step_id in geometry:
            key = (group_of(e), GEOMETRY_QTO, "Volume", "geometry")
            values[key][e.global_id] = geometry[e.step_id]
            units[key] = "m3"
    members: dict[tuple[str, str], list[str]] = defaultdict(list)  # (group, class) -> GlobalIds
    for e in snap.elements:
        members[(group_of(e), e.ifc_class)].append(e.global_id)
    classes = {e.global_id: e.ifc_class for e in snap.elements}
    return tuple(_row(k, v, units[k], members, classes) for k, v in sorted(values.items()))


def _row(key: tuple, vals: dict[str, float], unit: str | None, members: dict, classes: dict) -> QuantityRow:
    group, qto, name, method = key
    pool = {g for cls in {classes[g] for g in vals} for g in members[(group, cls)]}
    missing = tuple(sorted(pool - vals.keys()))
    return QuantityRow(group, qto, name, method, unit, math.fsum(vals.values()), len(vals), missing)


def quantity_delta(old: tuple[QuantityRow, ...], new: tuple[QuantityRow, ...]) -> tuple[QuantityDelta, ...]:
    a = {(r.group, r.qto, r.quantity, r.method): r for r in old}
    b = {(r.group, r.qto, r.quantity, r.method): r for r in new}
    return tuple(
        QuantityDelta(
            *k, (b.get(k) or a[k]).unit, a[k].total if k in a else None, b[k].total if k in b else None
        )
        for k in sorted(a.keys() | b.keys())
    )
