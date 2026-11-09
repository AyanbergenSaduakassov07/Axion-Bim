from collections import defaultdict

import pytest

from axiom.extract import extract
from axiom.findings import CheckStatus, identity_key
from axiom.rules import CheckResult, RuleMeta, Scope, builtin_rules, run_rules
from axiom.rules.engine import is_subclass
from tests.conftest import load_expected
from tests.test_fixtures import FIXTURES

# Hand-authored defect lists in expected/*.yaml -> the rule that must report them.
DEFECT_RULE = {"missing_material": "MAT-001", "no_geometry": "GEO-001", "uncontained": "SPA-001"}


def findings_by_rule(output) -> dict[str, list]:
    got: dict[str, list] = defaultdict(list)
    for f in output.findings:
        got[f.rule_id].append(f.evidence["names"] if f.rule_id == "GEO-002" else f.element_name)
    return {k: sorted(v) for k, v in got.items()}


@pytest.mark.parametrize("name", FIXTURES)
def test_fixture_produces_exactly_its_expected_findings(name, ifc_path):
    defects = load_expected(name)["defects"]
    want = {rule: sorted(defects[key]) for key, rule in DEFECT_RULE.items() if defects[key]}
    if defects["duplicate_guid"]:
        want["GEO-002"] = sorted(sorted(g) for g in defects["duplicate_guid"])
    assert findings_by_rule(run_rules(extract(ifc_path(name)), model_id=1)) == want


def test_findings_carry_evidence_and_stable_identity(ifc_path):
    out = run_rules(extract(ifc_path("missing_material")), model_id=7)
    c2 = next(f for f in out.findings if f.element_name == "C2")
    assert (c2.rule_id, c2.status, c2.severity, c2.issue_key) == (
        "MAT-001",
        "fail",
        "high",
        "material:missing",
    )
    assert c2.identity_key == identity_key(7, "MAT-001", c2.global_id, "material:missing")
    assert c2.expected and c2.actual is not None and c2.rule_version


def test_counts_cover_every_rule_and_status(ifc_path):
    out = run_rules(extract(ifc_path("missing_material")), model_id=1)
    assert out.counts["MAT-001"] == {"pass": 8, "fail": 2}  # 4 columns + 4 beams + 2 slabs
    assert set(out.counts) == {r.meta.id for r in builtin_rules()}


def test_rule_exception_becomes_error_not_crash(ifc_path):
    def boom(element, ctx):
        raise ValueError("bad rule")

    broken = RuleMeta("TST-001", "1", "boom", "metadata", "low", "naming", Scope.ELEMENT, ("IfcColumn",), "x")
    out = run_rules(extract(ifc_path("clean")), model_id=1, rules=[(broken, boom)])
    assert out.counts["TST-001"] == {"error": 4}
    assert all(f.status == CheckStatus.ERROR and "bad rule" in f.message for f in out.findings)


def test_containment_not_evaluated_when_model_has_no_storeys(ifc_path):
    snap = extract(ifc_path("clean"))
    no_storeys = snap.model_copy(
        update={"spatial": tuple(n for n in snap.spatial if n.ifc_class != "IfcBuildingStorey")}
    )
    assert run_rules(no_storeys, model_id=1).counts["SPA-001"] == {"not_evaluated": 16}


def test_aggregate_parent_with_geometric_children_passes_geometry(ifc_path):
    snap = extract(ifc_path("no_geometry"))
    b3 = next(e for e in snap.elements if e.name == "B3")
    els = tuple(
        e.model_copy(update={"parent_global_id": b3.global_id}) if e.name == "C1" else e
        for e in snap.elements
    )
    out = run_rules(snap.model_copy(update={"elements": els}), model_id=1)
    assert findings_by_rule(out)["GEO-001"] == ["B4"]


def test_subclasses_match_parent_applicability(ifc_path):
    snap = extract(ifc_path("missing_material"))
    els = tuple(
        e.model_copy(update={"ifc_class": "IfcColumnStandardCase"}) if e.name == "C2" else e
        for e in snap.elements
    )
    assert (
        "C2" in findings_by_rule(run_rules(snap.model_copy(update={"elements": els}), model_id=1))["MAT-001"]
    )


def test_check_result_defaults():
    assert CheckResult(CheckStatus.PASS).evidence == {}


def test_containment_uses_facility_structure_when_model_has_no_storeys(ifc_path):
    """IFC 4.3 infrastructure: elements sit in IfcFacility / IfcFacilityPart, never in a storey."""
    snap = extract(ifc_path("clean"))
    storey = next(n for n in snap.spatial if n.ifc_class == "IfcBuildingStorey")
    infra = snap.model_copy(
        update={
            "spatial": tuple(
                n.model_copy(update={"ifc_class": "IfcBridgePart"})
                if n.ifc_class == "IfcBuildingStorey"
                else n
                for n in snap.spatial
            ),
            "elements": tuple(
                e.model_copy(
                    update={
                        "storey_global_id": None,
                        "container_global_id": None if e.name == "C1" else storey.global_id,
                    }
                )
                for e in snap.elements
            ),
        }
    )
    counts = run_rules(infra, model_id=1).counts["SPA-001"]
    assert counts == {"pass": 15, "fail": 1}


@pytest.mark.parametrize("schema", ["IFC2X3", "IFC4", "IFC4X3", "IFC4X3_ADD2"])
def test_subclass_check_resolves_every_supported_schema_name(schema):
    """IFC 4.3 files declare FILE_SCHEMA('IFC4X3'); ifcopenshell registers it as IFC4X3_ADD2."""
    assert is_subclass(schema, "IfcColumn", "IfcElement")


def test_aggregated_parts_take_name_and_classification_from_their_parent(ifc_path):
    """ArchiCAD layer parts (IfcBuildingElementPart in an IfcRelAggregates) are unnamed by design."""
    snap = extract(ifc_path("clean"))
    parent = next(e for e in snap.elements if e.name == "W1")
    part = parent.model_copy(
        update={"global_id": "0PartOfW1xxxxxxxxxxxxx", "step_id": 999999,
                "ifc_class": "IfcBuildingElementPart", "name": None, "classifications": (),
                "parent_global_id": parent.global_id}
    )  # fmt: skip
    counts = run_rules(snap.model_copy(update={"elements": (*snap.elements, part)}), model_id=1).counts
    assert counts["MET-001"].get("not_applicable") == 1 and "fail" not in counts["MET-001"]
    assert counts["CLS-001"].get("not_applicable") == 1


def test_virtual_elements_are_not_extracted(tmp_path):
    import ifcopenshell.api  # noqa: PLC0415

    f = ifcopenshell.api.run("project.create_file", version="IFC4")
    ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcProject", name="P")
    ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcVirtualElement")
    ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcWall", name="W")
    f.write(str(tmp_path / "v.ifc"))
    assert [e.ifc_class for e in extract(tmp_path / "v.ifc").elements] == ["IfcWall"]
