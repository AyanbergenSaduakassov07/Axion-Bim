"""Cross-model consistency inside one project (audit gap G5): do the discipline models share units,
georeferencing and storey levels? Pure functions over facts already in each revision's snapshot.

A difference is reported per model. Nothing here is geometry or clash detection.
"""

from __future__ import annotations

from dataclasses import dataclass

STOREY_TOLERANCE_M = 0.01  # storeys closer than this are the same level
DECISION_RANK = ("accepted", "accepted_with_comments", "undecided", "rejected")  # best -> worst


@dataclass(frozen=True)
class ModelFacts:
    name: str
    length_unit: str | None
    georef: dict | None
    storeys: tuple[tuple[str | None, float | None], ...]  # (name, elevation in metres)


def worst_decision(decisions: list[str | None]) -> str:
    """Project decision = worst model decision. A model with no audited delivery leaves it undecided."""
    if not decisions:
        return "undecided"
    return max((d or "undecided" for d in decisions), key=DECISION_RANK.index)


def check(models: list[ModelFacts]) -> list[dict]:
    return [_same("length_unit", models, lambda m: m.length_unit), _georef(models), _storeys(models)]


def _result(name: str, status: str, actual: dict) -> dict:
    return {"check": name, "status": status, "actual": actual}


def _same(name: str, models: list[ModelFacts], value) -> dict:
    actual = {m.name: value(m) for m in models}
    known = [v for v in actual.values() if v is not None]
    if len(models) < 2 or not known:
        return _result(name, "not_evaluated", actual)
    same = len(known) == len(models) and all(v == known[0] for v in known)
    return _result(name, "pass" if same else "fail", actual)


def _georef(models: list[ModelFacts]) -> dict:
    # a model without georeferencing next to one that has it cannot be placed together: that is a fail
    return _same("georeferencing", models, lambda m: m.georef)


def _storeys(models: list[ModelFacts]) -> dict:
    """Levels of one model that no other model has within tolerance. Different storey sets can be
    legitimate (a structural model with a foundation level), so a mismatch is a warning, not a fail."""
    levels = {m.name: sorted({e for _, e in m.storeys if e is not None}) for m in models}
    with_levels = [n for n, v in levels.items() if v]
    if len(with_levels) < 2:
        return _result("storey_elevations", "not_evaluated", levels)
    unmatched = {
        n: [e for e in levels[n] if not all(_has_level(levels[o], e) for o in with_levels if o != n)]
        for n in with_levels
    }
    status = "warning" if any(unmatched.values()) else "pass"
    return _result("storey_elevations", status, unmatched if status == "warning" else levels)


def _has_level(levels: list[float], elevation: float) -> bool:
    return any(abs(e - elevation) <= STOREY_TOLERANCE_M for e in levels)
