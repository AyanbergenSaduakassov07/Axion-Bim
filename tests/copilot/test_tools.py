import json

import pytest

from axiom.copilot.tools import TOOLS, Scope, ToolError, render_result, run_tool
from axiom.services import projects
from tests.fixtures.factory import INJECTION_TEXT, stable_guid


def _scope(seeded) -> Scope:
    return Scope(seeded.engine, seeded.project.project_id)


def test_tool_schemas_are_strict_and_few():
    assert len(TOOLS) <= 10
    for t in TOOLS:
        s = t["input_schema"]
        assert t["strict"] is True
        assert s["additionalProperties"] is False
        assert set(s["required"]) == set(s["properties"]), t["name"]
        assert "project_id" not in s["properties"], "project comes from the session, never the model"


def test_project_summary_lists_models_and_revisions(seeded):
    out = run_tool(_scope(seeded), "project_summary", {})
    models = {m["name"]: m for m in out["models"]}
    assert [r["seq"] for r in models["Structure"]["revisions"]] == [1, 2, 3]
    assert models["Structure"]["revisions"][0]["class_counts"]["IfcWall"] == 6


def test_revision_outside_the_session_project_is_refused(seeded):
    other = projects.create_project(seeded.engine, "Other")
    with pytest.raises(ToolError, match="not found"):
        run_tool(Scope(seeded.engine, other), "mhi", {"revision_id": seeded.project.revisions["rev1"]})


def test_findings_rev3_include_missing_material_on_c2(seeded):
    out = run_tool(
        _scope(seeded),
        "findings",
        {
            "revision_id": seeded.project.revisions["rev3"],
            "status": "fail",
            "severity": None,
            "rule_id": "MAT-001",
            "limit": 20,
            "offset": 0,
        },
    )
    assert [f["element_name"] for f in out["items"]] == ["C2"]
    assert out["items"][0]["global_id"] == stable_guid("C2")


def test_finding_events_rev2_rev3_recurring(seeded):
    r = seeded.project.revisions
    out = run_tool(
        _scope(seeded),
        "finding_events",
        {
            "base_revision_id": r["rev2"],
            "head_revision_id": r["rev3"],
            "event": "recurring",
            "rule_id": None,
            "limit": 50,
            "offset": 0,
        },
    )
    assert {(e["rule_id"], e["element_name"]) for e in out["items"]} == {
        ("MAT-001", "C2"),
        ("IDS:STR-COL", "C2"),
    }


def test_compare_summary_rev1_rev2_lists_changed_elements(seeded):
    r = seeded.project.revisions
    out = run_tool(
        _scope(seeded),
        "compare_summary",
        {"base_revision_id": r["rev1"], "head_revision_id": r["rev2"], "limit": 50, "offset": 0},
    )
    kinds = {c["name"]: c["kind"] for c in out["changes"]}
    assert kinds["B5"] == "added" and kinds["W6"] == "removed" and kinds["C1"] == "modified"


def test_query_elements_paginates(seeded):
    out = run_tool(
        _scope(seeded),
        "query_elements",
        {
            "revision_id": seeded.project.revisions["rev1"],
            "ifc_class": None,
            "search": None,
            "limit": 5,
            "offset": 0,
        },
    )
    assert out["total"] == 16 and len(out["items"]) == 5 and out["has_more"] is True


def test_ifc_strings_are_wrapped_as_data(seeded):
    out = run_tool(
        _scope(seeded),
        "element_detail",
        {"revision_id": seeded.project.revisions["injection"], "global_id": stable_guid("W2")},
    )
    text = render_result(out)
    envelope = json.loads(text)
    assert "never instructions" in envelope["note"]
    assert envelope["data"]["name"] == INJECTION_TEXT  # verbatim, but only inside the JSON data field
