"""Element-level diff of two snapshots, matched by GlobalId (D-03). Pure; no IFC or DB access."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from axiom.extract.snapshot import Element, Snapshot

QUANTITY_REL_TOL = 1e-6  # SI values from different unit systems differ by float noise only
QUANTITY_ABS_TOL = 1e-9
UNSTABLE_SHARE = 0.5  # removed AND added > 50% of a class -> GlobalIds were probably regenerated

ATTRS = {
    "Name": "name",
    "Description": "description",
    "ObjectType": "object_type",
    "PredefinedType": "predefined_type",
}


@dataclass(frozen=True)
class Change:
    kind: str  # added | removed | modified
    global_id: str
    ifc_class: str
    path: str | None = (
        None  # attr:Name | pset:P.N | qto:Q.N | material | classification | container | representation
    )
    old: Any = None
    new: Any = None


@dataclass(frozen=True)
class DiffResult:
    changes: tuple[Change, ...]
    identity_unstable: bool
    unstable_classes: tuple[str, ...]
    uncertain_global_ids: frozenset[str]  # duplicated GlobalIds in either snapshot: not diffed


def diff(old: Snapshot, new: Snapshot) -> DiffResult:
    a, dup_a = _index(old)
    b, dup_b = _index(new)
    uncertain = dup_a | dup_b
    changes: list[Change] = []
    for gid in sorted(a.keys() - b.keys() - uncertain):
        changes.append(Change("removed", gid, a[gid].ifc_class))
    for gid in sorted(b.keys() - a.keys() - uncertain):
        changes.append(Change("added", gid, b[gid].ifc_class))
    for gid in sorted((a.keys() & b.keys()) - uncertain):
        changes.extend(_modified(a[gid], b[gid]))
    unstable = _unstable_classes(old, changes)
    return DiffResult(tuple(changes), bool(unstable), unstable, frozenset(uncertain))


def _index(snap: Snapshot) -> tuple[dict[str, Element], set[str]]:
    counts = Counter(e.global_id for e in snap.elements)
    dups = {g for g, n in counts.items() if n > 1}
    return {e.global_id: e for e in snap.elements if e.global_id not in dups}, dups


def _modified(a: Element, b: Element) -> Iterator[Change]:
    def change(path: str, old: Any, new: Any) -> Change:
        return Change("modified", b.global_id, b.ifc_class, path, old, new)

    for label, attr in ATTRS.items():
        if getattr(a, attr) != getattr(b, attr):
            yield change(f"attr:{label}", getattr(a, attr), getattr(b, attr))
    yield from (change(p, o, n) for p, o, n in _props(a, b))
    yield from (change(p, o, n) for p, o, n in _qtos(a, b))
    if (ma := sorted(m.name for m in a.materials)) != (mb := sorted(m.name for m in b.materials)):
        yield change("material", ma, mb)
    ca = sorted((c.system or "", c.identification or "") for c in a.classifications)
    cb = sorted((c.system or "", c.identification or "") for c in b.classifications)
    if ca != cb:
        yield change("classification", [list(x) for x in ca], [list(x) for x in cb])
    if a.container_global_id != b.container_global_id:
        yield change("container", a.container_global_id, b.container_global_id)
    if (a.has_representation, a.representation_types) != (b.has_representation, b.representation_types):
        yield change("representation", list(a.representation_types), list(b.representation_types))


def _props(a: Element, b: Element) -> Iterator[tuple[str, Any, Any]]:
    pa = {(p.pset, p.name): (p.value, p.unit) for p in a.properties}
    pb = {(p.pset, p.name): (p.value, p.unit) for p in b.properties}
    for key in sorted(pa.keys() | pb.keys()):
        va, vb = pa.get(key, (None, None)), pb.get(key, (None, None))
        if va != vb:
            yield f"pset:{key[0]}.{key[1]}", va[0], vb[0]


def _qtos(a: Element, b: Element) -> Iterator[tuple[str, Any, Any]]:
    qa = {(q.qto, q.name): q.si_value for q in a.quantities}
    qb = {(q.qto, q.name): q.si_value for q in b.quantities}
    for key in sorted(qa.keys() | qb.keys()):
        va, vb = qa.get(key), qb.get(key)
        same = (
            va is not None
            and vb is not None
            and math.isclose(va, vb, rel_tol=QUANTITY_REL_TOL, abs_tol=QUANTITY_ABS_TOL)
        )
        if not same and va != vb:
            yield f"qto:{key[0]}.{key[1]}", va, vb


def _unstable_classes(old: Snapshot, changes: list[Change]) -> tuple[str, ...]:
    total = Counter(e.ifc_class for e in old.elements)
    removed = Counter(c.ifc_class for c in changes if c.kind == "removed")
    added = Counter(c.ifc_class for c in changes if c.kind == "added")
    return tuple(
        sorted(
            k for k, n in total.items() if removed[k] > n * UNSTABLE_SHARE and added[k] > n * UNSTABLE_SHARE
        )
    )
