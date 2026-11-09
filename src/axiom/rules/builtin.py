"""Built-in rule set v1. Missing information is an information deficiency, never a safety statement."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from axiom.extract.snapshot import Element
from axiom.findings import CheckStatus
from axiom.rules.engine import CheckResult, ModelContext, Scope, rule

PASS = CheckResult(CheckStatus.PASS)
NOT_APPLICABLE = CheckResult(CheckStatus.NOT_APPLICABLE)
GEOMETRIC = ("IfcWall", "IfcColumn", "IfcBeam", "IfcSlab", "IfcMember", "IfcFooting")
STRUCTURAL = ("IfcColumn", "IfcBeam", "IfcSlab", "IfcFooting", "IfcMember")


def _has_geometry(el: Element, ctx: ModelContext) -> bool:
    return el.has_representation or any(_has_geometry(c, ctx) for c in ctx.children.get(el.global_id, ()))


@rule(
    id="GEO-001",
    version="1",
    name="Element has a body representation",
    category="geometry",
    severity="high",
    dimension="geometry",
    applies_to=GEOMETRIC,
    description="IfcProduct.Representation present; an aggregate (IfcRelAggregates) passes if a part has it.",
)
def geo_001(el: Element, ctx: ModelContext) -> CheckResult:
    """IFC: IfcProduct.Representation; assemblies such as IfcCurtainWall/IfcStair carry geometry on parts."""
    if _has_geometry(el, ctx):
        return PASS
    return CheckResult(
        CheckStatus.FAIL,
        "geometry:missing",
        expected="body representation",
        actual="none",
        message=f"{el.ifc_class} has no geometric representation",
    )


@rule(
    id="GEO-002",
    version="1",
    name="GlobalId is unique",
    category="identity",
    severity="critical",
    dimension="identity",
    scope=Scope.MODEL,
    description="IfcRoot.GlobalId must be unique in the file; duplicates break revision tracking.",
)
def geo_002(ctx: ModelContext) -> Iterable[tuple[Element | None, CheckResult]]:
    """IFC: IfcRoot.GlobalId uniqueness. One finding per duplicated id, not per element."""
    for gid, els in sorted(ctx.by_global_id.items()):
        if len(els) == 1:
            yield els[0], PASS
            continue
        yield (
            None,
            CheckResult(
                CheckStatus.FAIL,
                "guid:duplicate",
                expected="unique GlobalId",
                actual=f"{len(els)} elements",
                message=f"GlobalId {gid} is shared by {len(els)} elements",
                evidence={
                    "global_id": gid,
                    "names": sorted(e.name or "" for e in els),
                    "step_ids": sorted(e.step_id for e in els),
                },
            ),
        )


@rule(
    id="SPA-001",
    version="2",
    name="Element is contained in the spatial structure",
    category="spatial",
    severity="medium",
    dimension="spatial",
    applies_to=("IfcElement",),
    description=(
        "Buildings: IfcRelContainedInSpatialStructure to an IfcBuildingStorey, directly or via an aggregate. "
        "IFC 4.3 infrastructure (no storeys, has IfcFacility/-Part): contained in any spatial element."
    ),
)
def spa_001(el: Element, ctx: ModelContext) -> CheckResult:
    """IFC: IfcRelContainedInSpatialStructure (+ IfcRelAggregates parent chain)."""
    if ctx.storey_ids:
        if el.storey_global_id:
            return PASS
        return _uncontained(el, "a storey", "building storey")
    if ctx.facility_ids:
        if el.container_global_id:
            return PASS
        return _uncontained(el, "a spatial element", "facility or spatial element")
    return CheckResult(
        CheckStatus.NOT_EVALUATED,
        "storey:none_in_model",
        message="model has no IfcBuildingStorey or IfcFacility; containment cannot be assessed",
    )


def _uncontained(el: Element, expected: str, where: str) -> CheckResult:
    return CheckResult(
        CheckStatus.FAIL,
        "spatial:uncontained",
        expected=f"contained in {expected}",
        actual=f"container {el.container_global_id or 'none'}",
        message=f"{el.ifc_class} is not located in any {where}",
    )


@rule(
    id="SPA-002",
    version="1",
    name="Storeys have unique names and elevations",
    category="spatial",
    severity="high",
    dimension="spatial",
    scope=Scope.MODEL,
    description="IfcBuildingStorey.Name unique and IfcBuildingStorey.Elevation distinct.",
)
def spa_002(ctx: ModelContext) -> Iterable[tuple[Element | None, CheckResult]]:
    """IFC: IfcBuildingStorey.Name / .Elevation. Elevation missing -> not_evaluated for that storey."""
    storeys = [n for n in ctx.snapshot.spatial if n.ifc_class == "IfcBuildingStorey"]
    names, elevations = defaultdict(list), defaultdict(list)
    for s in storeys:
        names[s.name].append(s)
        if s.elevation_m is not None:
            elevations[round(s.elevation_m, 3)].append(s)
    for s in storeys:
        ev = {"global_id": s.global_id, "storey": s.name}
        if len(names[s.name]) > 1:
            yield (
                None,
                CheckResult(
                    CheckStatus.FAIL,
                    "storey:duplicate_name",
                    "unique storey name",
                    s.name,
                    f"storey name '{s.name}' is used more than once",
                    ev,
                ),
            )
        elif s.elevation_m is None:
            yield None, CheckResult(CheckStatus.NOT_EVALUATED, "storey:no_elevation", evidence=ev)
        elif len(elevations[round(s.elevation_m, 3)]) > 1:
            yield (
                None,
                CheckResult(
                    CheckStatus.FAIL,
                    "storey:duplicate_elevation",
                    "distinct elevation",
                    f"{s.elevation_m:g} m",
                    f"storey '{s.name}' shares its elevation",
                    ev,
                ),
            )
        else:
            yield None, PASS


@rule(
    id="MAT-001",
    version="1",
    name="Structural element has a material",
    category="material",
    severity="high",
    dimension="material",
    applies_to=STRUCTURAL,
    description="IfcRelAssociatesMaterial present (material, layer/profile/constituent set or list).",
)
def mat_001(el: Element, ctx: ModelContext) -> CheckResult:
    """IFC: IfcRelAssociatesMaterial, incl. type-inherited material."""
    if el.materials:
        return PASS
    return CheckResult(
        CheckStatus.FAIL,
        "material:missing",
        expected="material association",
        actual="none",
        message=f"{el.ifc_class} has no material assigned",
    )


@rule(
    id="MET-001",
    version="2",
    name="Element has a name",
    category="metadata",
    severity="low",
    dimension="naming",
    applies_to=("IfcElement",),
    description="IfcRoot.Name is non-empty. Aggregated IfcBuildingElementPart: not applicable.",
)
def met_001(el: Element, ctx: ModelContext) -> CheckResult:
    """IFC: IfcRoot.Name."""
    if _is_part(el):
        return NOT_APPLICABLE
    if el.name and el.name.strip():
        return PASS
    return CheckResult(
        CheckStatus.FAIL,
        "name:missing",
        expected="non-empty Name",
        actual=repr(el.name),
        message=f"{el.ifc_class} has no Name",
    )


@rule(
    id="CLS-001",
    version="2",
    name="Element has a classification reference",
    category="classification",
    severity="low",
    dimension="classification",
    applies_to=("IfcElement",),
    description=(
        "IfcRelAssociatesClassification present. Warning only: many valid models omit it. "
        "Aggregated IfcBuildingElementPart: not applicable (the parent is classified)."
    ),
)
def cls_001(el: Element, ctx: ModelContext) -> CheckResult:
    """IFC: IfcRelAssociatesClassification -> IfcClassificationReference."""
    if _is_part(el):
        return NOT_APPLICABLE
    if el.classifications:
        return PASS
    return CheckResult(
        CheckStatus.WARNING,
        "classification:missing",
        expected="classification reference",
        actual="none",
        message=f"{el.ifc_class} has no classification reference",
    )


def _is_part(el: Element) -> bool:
    # layer/component parts of an aggregate (ArchiCAD composites): identity lives on the parent element
    return el.ifc_class == "IfcBuildingElementPart" and el.parent_global_id is not None


def _is_base_qto(name: str) -> bool:
    # IFC4 Qto_<X>BaseQuantities; IFC2x3-era exporters (e.g. Revit) write "BaseQuantities"
    return name == "BaseQuantities" or (name.startswith("Qto_") and name.endswith("BaseQuantities"))


@rule(
    id="QTO-001",
    version="1",
    name="Element has base quantities",
    category="quantity",
    severity="medium",
    dimension="quantity",
    applies_to=GEOMETRIC,
    description="IfcElementQuantity named Qto_*BaseQuantities with at least one quantity.",
)
def qto_001(el: Element, ctx: ModelContext) -> CheckResult:
    """IFC: IfcRelDefinesByProperties -> IfcElementQuantity (Qto_*BaseQuantities)."""
    if any(_is_base_qto(q.qto) for q in el.quantities):
        return PASS
    return CheckResult(
        CheckStatus.FAIL,
        "qto:base_missing",
        expected="Qto_*BaseQuantities",
        actual="none",
        message=f"{el.ifc_class} has no base quantity set",
    )
