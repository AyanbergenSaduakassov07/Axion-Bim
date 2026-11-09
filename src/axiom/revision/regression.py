"""Finding regression across revisions (D-03): classify each finding by identity_key. Pure."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from axiom.findings import Finding
from axiom.revision.diff import DiffResult


@dataclass(frozen=True)
class FindingEvent:
    event: str  # new | resolved | persistent | recurring | changed | uncertain
    identity_key: str
    rule_id: str
    global_id: str | None
    element_name: str | None
    severity: str
    note: str | None = None


def classify(
    current: Iterable[Finding],
    history: Sequence[Iterable[Finding]],
    d: DiffResult | None = None,
    evaluated: tuple[set[str], set[str]] | None = None,
    version_changed: Iterable[str] = (),
) -> tuple[FindingEvent, ...]:
    """history: reported findings of earlier revisions, oldest first; history[-1] is the compared one.
    evaluated: (rule ids run on base, rule ids run on head). A rule run on one side only cannot
    resolve or introduce a finding, so its events are uncertain.
    version_changed: rule ids whose version differs between the audits; their new/resolved/changed
    events may come from the rule, not the model, so they are uncertain."""
    changed_rules = set(version_changed)
    base_rules, head_rules = evaluated or (None, None)
    prev = {f.identity_key: f for f in history[-1]} if history else {}
    earlier = {f.identity_key for h in history[:-1] for f in h}
    removed = {c.global_id for c in d.changes if c.kind == "removed"} if d else set()

    def uncertain(f: Finding) -> bool:
        return d is not None and (d.identity_unstable or f.global_id in d.uncertain_global_ids)

    events: list[FindingEvent] = []
    seen: set[str] = set()
    for f in current:
        seen.add(f.identity_key)
        if uncertain(f):
            kind = "uncertain"
        elif base_rules is not None and f.rule_id not in base_rules:
            events.append(_event("uncertain", f, "rule_not_evaluated_in_base"))
            continue
        elif (p := prev.get(f.identity_key)) is not None:
            same = (p.status, p.severity, p.actual, p.evidence) == (
                f.status,
                f.severity,
                f.actual,
                f.evidence,
            )
            kind = "persistent" if same else "changed"
        else:
            kind = "recurring" if f.identity_key in earlier else "new"
        if kind not in {"persistent", "uncertain"} and f.rule_id in changed_rules:
            events.append(_event("uncertain", f, "rule_version_changed"))
            continue
        events.append(_event(kind, f))
    for key, p in prev.items():
        if key not in seen and head_rules is not None and p.rule_id not in head_rules:
            events.append(_event("uncertain", p, "rule_not_evaluated_in_head"))
        elif key not in seen and p.rule_id in changed_rules and not uncertain(p):
            events.append(_event("uncertain", p, "rule_version_changed"))
        elif key not in seen:
            note = "element_removed" if p.global_id in removed else None
            events.append(_event("uncertain" if uncertain(p) else "resolved", p, note))
    return tuple(events)


def _event(kind: str, f: Finding, note: str | None = None) -> FindingEvent:
    return FindingEvent(kind, f.identity_key, f.rule_id, f.global_id, f.element_name, f.severity, note)


@dataclass(frozen=True)
class Impact:
    """A finding event on an element that also changed: "material changed on C2 -> MAT-001 resolved"."""

    global_id: str
    element_name: str | None
    rule_id: str
    event: str
    paths: tuple[str, ...]  # change paths on the element; ("added",) / ("removed",) for whole elements


def impact(d: DiffResult, events: Iterable[FindingEvent]) -> tuple[Impact, ...]:
    paths: dict[str, list[str]] = {}
    for c in d.changes:
        paths.setdefault(c.global_id, []).append(c.path or c.kind)
    return tuple(
        Impact(e.global_id, e.element_name, e.rule_id, e.event, tuple(paths[e.global_id]))
        for e in events
        if e.event != "persistent" and e.global_id in paths
    )
