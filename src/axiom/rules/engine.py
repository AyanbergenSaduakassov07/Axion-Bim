"""Rule registry and runner. Rules never crash an audit: exceptions become `error` results."""

from __future__ import annotations

import hashlib
import logging
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from functools import cache
from typing import Any, NamedTuple

import ifcopenshell.ifcopenshell_wrapper as wrapper

from axiom.extract.snapshot import Element, Snapshot
from axiom.findings import CheckStatus, Finding, identity_key

log = logging.getLogger(__name__)


class Scope(StrEnum):
    ELEMENT = "element"  # fn(element, ctx) -> CheckResult
    MODEL = "model"  # fn(ctx) -> Iterable[(element | None, CheckResult)]


@dataclass(frozen=True)
class RuleMeta:
    id: str
    version: str
    name: str
    category: str
    severity: str
    dimension: str
    scope: Scope
    applies_to: tuple[str, ...]  # IFC classes incl. subclasses; ignored for MODEL scope
    description: str


@dataclass(frozen=True)
class CheckResult:
    status: CheckStatus
    issue_key: str = ""
    expected: str | None = None
    actual: str | None = None
    message: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)


class Rule(NamedTuple):
    meta: RuleMeta
    fn: Callable


FACILITY_CLASSES = frozenset({
    "IfcFacility", "IfcBridge", "IfcRoad", "IfcRailway", "IfcMarineFacility",
    "IfcFacilityPart", "IfcFacilityPartCommon", "IfcBridgePart", "IfcRoadPart", "IfcRailwayPart",
    "IfcMarinePart",
})  # fmt: skip


@dataclass(frozen=True)
class ModelContext:
    """Indexes built once per audit so rules stay O(1) per element."""

    snapshot: Snapshot
    children: dict[str, tuple[Element, ...]]
    by_global_id: dict[str, tuple[Element, ...]]
    storey_ids: frozenset[str]
    facility_ids: frozenset[str]  # IFC 4.3 infrastructure spatial structure (facilities and their parts)

    @classmethod
    def build(cls, snap: Snapshot) -> ModelContext:
        children: dict[str, list[Element]] = defaultdict(list)
        by_gid: dict[str, list[Element]] = defaultdict(list)
        for e in snap.elements:
            by_gid[e.global_id].append(e)
            if e.parent_global_id:
                children[e.parent_global_id].append(e)
        storeys = frozenset(n.global_id for n in snap.spatial if n.ifc_class == "IfcBuildingStorey")
        facilities = frozenset(n.global_id for n in snap.spatial if n.ifc_class in FACILITY_CLASSES)
        return cls(
            snap,
            {k: tuple(v) for k, v in children.items()},
            {k: tuple(v) for k, v in by_gid.items()},
            storeys,
            facilities,
        )


@dataclass(frozen=True)
class AuditOutput:
    findings: tuple[Finding, ...]  # non-pass results only: fail | warning | error
    counts: dict[str, dict[str, int]]  # rule id -> status -> n (all statuses, incl. pass)
    ruleset_version: str
    rules: tuple[RuleMeta, ...]


REGISTRY: dict[str, Rule] = {}
REPORTED = frozenset({CheckStatus.FAIL, CheckStatus.WARNING, CheckStatus.ERROR})


def rule(**meta: Any) -> Callable[[Callable], Callable]:
    def register(fn: Callable) -> Callable:
        m = RuleMeta(**{"scope": Scope.ELEMENT, "applies_to": (), **meta})
        if m.id in REGISTRY:
            raise ValueError(f"duplicate rule id {m.id}")
        REGISTRY[m.id] = Rule(m, fn)
        return fn

    return register


def builtin_rules() -> tuple[Rule, ...]:
    import axiom.rules.builtin  # noqa: F401, PLC0415 - registration side effect, deferred to avoid a cycle

    return tuple(REGISTRY[k] for k in sorted(REGISTRY))


def ruleset_version(rules: Iterable[Rule]) -> str:
    raw = "|".join(f"{r.meta.id}@{r.meta.version}" for r in sorted(rules, key=lambda r: r.meta.id))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@cache
def _schema(name: str):  # noqa: ANN202 - ifcopenshell wrapper type
    """FILE_SCHEMA names the release ('IFC4X3'); ifcopenshell registers the addendum ('IFC4X3_ADD2')."""
    addenda = sorted(n for n in wrapper.schema_names() if n.upper().startswith(f"{name.upper()}_"))
    return wrapper.schema_by_name(addenda[-1] if addenda else name)


@cache
def is_subclass(schema: str, ifc_class: str, parent: str) -> bool:
    try:
        decl = _schema(schema).declaration_by_name(ifc_class)
    except (RuntimeError, IndexError):  # unknown class name in this schema
        return ifc_class == parent
    while decl is not None:
        if decl.name() == parent:
            return True
        decl = decl.supertype()
    return False


def run_rules(snap: Snapshot, model_id: int, rules: Iterable[Rule] | None = None) -> AuditOutput:
    rules = tuple(Rule(*r) for r in (builtin_rules() if rules is None else rules))
    ctx = ModelContext.build(snap)
    findings: list[Finding] = []
    counts: dict[str, Counter] = {}
    for r in rules:
        counts[r.meta.id] = Counter()
        for element, result in _evaluate(r, ctx):
            counts[r.meta.id][result.status.value] += 1
            if result.status in REPORTED:
                findings.append(_finding(model_id, r.meta, element, result))
    return AuditOutput(
        tuple(findings),
        {k: dict(v) for k, v in counts.items()},
        ruleset_version(rules),
        tuple(r.meta for r in rules),
    )


def _evaluate(r: Rule, ctx: ModelContext) -> Iterable[tuple[Element | None, CheckResult]]:
    if r.meta.scope is Scope.MODEL:
        try:
            yield from r.fn(ctx)
        except Exception as e:  # noqa: BLE001 - a broken rule must not abort the audit
            log.exception("rule %s failed", r.meta.id)
            yield None, _error(e)
        return
    schema = ctx.snapshot.meta.schema_name
    for el in ctx.snapshot.elements:
        if not any(is_subclass(schema, el.ifc_class, c) for c in r.meta.applies_to):
            continue
        try:
            yield el, r.fn(el, ctx)
        except Exception as e:  # noqa: BLE001 - a broken rule must not abort the audit
            log.warning("rule %s failed on %s: %s", r.meta.id, el.global_id, e)
            yield el, _error(e)


def _error(e: Exception) -> CheckResult:
    return CheckResult(CheckStatus.ERROR, issue_key="rule:error", message=f"{type(e).__name__}: {e}")


def _finding(model_id: int, m: RuleMeta, el: Element | None, res: CheckResult) -> Finding:
    gid = el.global_id if el else res.evidence.get("global_id")
    return Finding(
        identity_key=identity_key(model_id, m.id, gid, res.issue_key),
        rule_id=m.id,
        rule_version=m.version,
        status=res.status,
        severity=m.severity,
        category=m.category,
        dimension=m.dimension,
        issue_key=res.issue_key,
        global_id=gid,
        step_id=el.step_id if el else None,
        ifc_class=el.ifc_class if el else None,
        element_name=el.name if el else None,
        expected=res.expected,
        actual=res.actual,
        message=res.message or m.name,
        evidence=res.evidence,
    )
