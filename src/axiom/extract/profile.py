"""Descriptive data-completeness profile of a Snapshot. Not a quality verdict: rules and MHI do that."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from axiom.extract.snapshot import Element, Snapshot

# shortcut: material is only expected on primary structural classes; make it per-ruleset config in P03.
MATERIAL_CLASSES = frozenset(
    {"IfcColumn", "IfcBeam", "IfcSlab", "IfcMember", "IfcFooting", "IfcPile", "IfcPlate"}
)
CHECKS: dict[str, Callable[[Element], bool]] = {
    "name": lambda e: bool(e.name),
    "psets": lambda e: bool(e.properties),
    "material": lambda e: bool(e.materials),
    "geometry": lambda e: e.has_representation,
    "containment": lambda e: e.container_global_id is not None,
}


def _applies(check: str, ifc_class: str) -> bool:
    return check != "material" or ifc_class in MATERIAL_CLASSES


def profile(snapshot: Snapshot) -> dict:
    groups: dict[str, list[Element]] = defaultdict(list)
    for e in snapshot.elements:
        groups[e.ifc_class].append(e)
    by_class = {cls: _class_profile(cls, els) for cls, els in sorted(groups.items())}
    applicable = sum(c["checks_applicable"] for c in by_class.values())
    passed = sum(c["checks_passed"] for c in by_class.values())
    return {
        "total_elements": len(snapshot.elements),
        "completeness": round(passed / applicable, 4) if applicable else None,
        "by_class": by_class,
    }


def _class_profile(cls: str, els: list[Element]) -> dict:
    missing = {
        name: (sum(not check(e) for e in els) if _applies(name, cls) else None)
        for name, check in CHECKS.items()
    }
    applicable = len(els) * sum(v is not None for v in missing.values())
    passed = applicable - sum(v for v in missing.values() if v is not None)
    return {
        "count": len(els),
        "missing": missing,
        "checks_applicable": applicable,
        "checks_passed": passed,
        "completeness": round(passed / applicable, 4) if applicable else None,
    }
