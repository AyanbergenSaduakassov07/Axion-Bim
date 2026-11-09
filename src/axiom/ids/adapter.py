"""IDS checks via IfcTester, mapped onto the shared Finding schema (D-04, D-12).

IfcTester decides every requirement; this module only translates its verdicts. Mapping:
- spec for another IFC schema -> not_applicable; spec the checker did not evaluate -> not_evaluated
- zero applicable entities -> fail if the spec is required (minOccurs>0), else not_applicable
- prohibited spec (maxOccurs=0) -> one fail per applicable entity
- otherwise one pass/fail per (applicable entity, requirement facet)
- entity facets match one exact class, so subclasses present in the file get a coverage warning
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import ifcopenshell
from ifctester import ids
from ifctester.facet import Entity
from xmlschema import XMLSchemaValidationError

from axiom.extract import file_sha256
from axiom.findings import CheckStatus, Finding, identity_key
from axiom.rules.engine import REPORTED, AuditOutput, RuleMeta, Scope

log = logging.getLogger(__name__)
IDS_NS = "http://standards.buildingsmart.org/IDS"

# facet attributes that name what a facet is about; values (and restrictions) are left out so keys stay stable
DESCRIPTOR = {
    "property": ("propertySet", "baseName"),
    "attribute": ("name",),
    "classification": ("system",),
    "material": ("value",),
    "partof": ("relation", "name"),
    "entity": ("name",),
}


@dataclass(frozen=True)
class IdsResult:
    status: CheckStatus
    issue_key: str
    severity: str = "high"
    element: Any = None  # ifcopenshell entity_instance or None for spec-level results
    expected: str | None = None
    actual: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


def load_ids(ids_path: Path) -> ids.Ids:
    """`ids.open(validate=True)` plus spec identifiers, which IfcTester 0.9.0 parses but drops."""
    schema = ids.get_schema()
    try:
        schema.validate(str(ids_path))
        raw = schema.decode(str(ids_path), strip_namespaces=True, namespaces={"": IDS_NS})
    except XMLSchemaValidationError as e:
        raise ValueError(f"invalid IDS file {Path(ids_path).name}: does not match the IDS 1.0 XSD") from e
    parsed = ids.Ids().parse(raw)
    xml_specs = raw["specifications"]["specification"]
    for spec, xml in zip(
        parsed.specifications, xml_specs if isinstance(xml_specs, list) else [xml_specs], strict=True
    ):
        spec.identifier = xml.get("@identifier")
    return parsed


def run_ids(ifc_path: Path, ids_path: Path, model_id: int) -> AuditOutput:
    version = file_sha256(Path(ids_path))[:12]
    specs = load_ids(ids_path)
    model = ifcopenshell.open(str(ifc_path))
    specs.validate(model, should_filter_version=True)
    findings: list[Finding] = []
    counts: dict[str, dict[str, int]] = {}
    metas: list[RuleMeta] = []
    for i, spec in enumerate(specs.specifications):
        meta = _meta(spec, version)
        if meta.id in counts:  # two specs share a name/identifier: keep both tallies
            meta = replace(meta, id=f"{meta.id}#{i}")
        tally: Counter = Counter()
        for r in _spec_results(i, spec, model):
            tally[r.status.value] += 1
            if r.status in REPORTED:
                findings.append(_finding(model_id, meta, spec, r))
        metas.append(meta)
        counts[meta.id] = dict(tally)
    log.info("IDS %s: %d specs, %d findings", Path(ids_path).name, len(metas), len(findings))
    return AuditOutput(tuple(findings), counts, version, tuple(metas))


def _meta(spec: ids.Specification, version: str) -> RuleMeta:
    return RuleMeta(
        id=f"IDS:{spec.identifier or spec.name}",
        version=version,
        name=spec.name,
        category="information",
        severity="high",
        dimension="information",
        scope=Scope.MODEL,
        applies_to=(),
        description=spec.description or "",
    )


def _spec_results(i: int, spec: ids.Specification, model: ifcopenshell.file) -> Iterator[IdsResult]:
    if not spec.is_ifc_version:
        yield IdsResult(CheckStatus.NOT_APPLICABLE, f"{i}/ifc_version")
        return
    if spec.status is None:
        yield IdsResult(CheckStatus.NOT_EVALUATED, f"{i}/not_evaluated")
        return
    applicable = spec.applicable_entities
    if not applicable:
        yield _empty(i, spec)
        return
    if spec.maxOccurs == 0:
        for el in applicable:
            yield IdsResult(
                CheckStatus.FAIL, f"{i}/applicability/prohibited", element=el,
                expected="no entities matching the applicability", actual=f"{el.is_a()} present",
            )  # fmt: skip
        return
    if not spec.requirements:
        yield from (IdsResult(CheckStatus.PASS, f"{i}/applicability", element=el) for el in applicable)
    for j, req in enumerate(spec.requirements):
        yield from _requirement_results(i, j, spec, req, applicable)
    yield from _coverage(i, spec, model)


def _empty(i: int, spec: ids.Specification) -> IdsResult:
    if spec.minOccurs == 0:
        return IdsResult(CheckStatus.NOT_APPLICABLE, f"{i}/applicability/none")
    return IdsResult(
        CheckStatus.FAIL, f"{i}/applicability/min_occurs",
        expected=f"at least {spec.minOccurs} entity matching the applicability", actual="0 matching entities",
    )  # fmt: skip


def _requirement_results(i: int, j: int, spec, req, applicable: list) -> Iterator[IdsResult]:
    kind = type(req).__name__.lower()
    key = f"{i}/{kind}/{_descriptor(req, kind)}"
    expected = req.to_string("requirement", spec, req)
    severity = "medium" if req.cardinality == "optional" else "high"
    reasons = {fl["element"].id(): fl["reason"] for fl in req.failures}
    for el in applicable:
        if el.id() in reasons:
            yield IdsResult(
                CheckStatus.FAIL, key, severity, el, expected, reasons[el.id()], {"requirement_index": j}
            )
        else:
            yield IdsResult(CheckStatus.PASS, key, severity, el)


def _descriptor(facet, kind: str) -> str:
    parts = [str(v) for a in DESCRIPTOR.get(kind, ()) if (v := getattr(facet, a, None)) is not None]
    return ".".join(parts) or "any"


def _coverage(i: int, spec: ids.Specification, model: ifcopenshell.file) -> Iterator[IdsResult]:
    for facet in spec.applicability:
        if not isinstance(facet, Entity) or not isinstance(facet.name, str):
            continue
        try:
            found = model.by_type(facet.name)
        except RuntimeError:  # class not in this schema
            continue
        uncovered = Counter(e.is_a() for e in found if e.is_a().upper() != facet.name.upper())
        if uncovered:
            yield IdsResult(
                CheckStatus.WARNING, f"{i}/coverage/subtypes", "info",
                expected=f"all {facet.name} subtypes checked",
                actual=f"{sum(uncovered.values())} subtype entities skipped",
                evidence={"entity": facet.name, "uncovered": dict(sorted(uncovered.items()))},
            )  # fmt: skip
            # skipped entities are coverage gaps: tallied, never reported as findings
            skipped = IdsResult(CheckStatus.NOT_EVALUATED, f"{i}/coverage/subtypes")
            yield from [skipped] * sum(uncovered.values())


def _finding(model_id: int, meta: RuleMeta, spec: ids.Specification, r: IdsResult) -> Finding:
    el = r.element
    gid = getattr(el, "GlobalId", None) if el is not None else None
    return Finding(
        identity_key=identity_key(model_id, meta.id, gid, r.issue_key),
        rule_id=meta.id,
        rule_version=meta.version,
        status=r.status,
        severity=r.severity,
        category=meta.category,
        dimension=meta.dimension,
        issue_key=r.issue_key,
        global_id=gid,
        step_id=el.id() if el is not None else None,
        ifc_class=el.is_a() if el is not None else None,
        element_name=getattr(el, "Name", None) if el is not None else None,
        expected=r.expected,
        actual=r.actual,
        message=f"{spec.name}: {r.actual or r.status}",
        evidence={"spec_index": int(r.issue_key.split("/")[0]), **r.evidence},
    )
