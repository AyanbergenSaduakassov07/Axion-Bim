"""BCF 3.0 export: one topic per open finding, element selected in a viewpoint, stable topic GUIDs."""

import zipfile

import pytest
from bcf.v2.bcfxml import BcfXml as BcfXml21
from bcf.v3.bcfxml import BcfXml

from axiom.report import render
from axiom.report.bcf import topic_guid
from tests.test_api import V1, _model, _upload, client  # noqa: F401 - client is a fixture


def _finding(status: str, gid: str | None, key: str, origin=None) -> dict:
    return {"origin_m": origin,
        "global_id": gid, "element_name": "C2", "ifc_class": "IfcColumn", "rule_id": "MAT-001",
        "rule_version": "1", "status": status, "severity": "high", "category": "material",
        "dimension": "completeness", "expected": "a material", "actual": "none",
        "message": "Element has no material", "identity_key": key, "evidence": {},
    }  # fmt: skip


REPORT = {
    "audit": {"id": 7, "revision": {"project_name": "Tower", "seq": 2}},
    "findings": [
        _finding("fail", "2O2Fr$t4X7Zf8NOew3FLOH", "k-fail", (10.0, 20.0, 3.0)),
        _finding("warning", None, "k-warn"),
        _finding("pass", "3cUkl32yn9qRSPvBJVyWYp", "k-pass"),
    ],
}


def _load(tmp_path, body: bytes) -> BcfXml:
    path = tmp_path / "a.bcf"
    path.write_bytes(body)
    return BcfXml.load(path)


def test_exports_one_topic_per_open_finding_with_element_viewpoint(tmp_path):
    bcf = _load(tmp_path, render(REPORT, "bcf"))
    topics = bcf.topics
    assert set(topics) == {topic_guid("k-fail"), topic_guid("k-warn")}  # pass is not an issue
    failing = topics[topic_guid("k-fail")]
    assert failing.topic.title.startswith("MAT-001")
    assert failing.topic.priority == "high"
    assert "a material" in failing.topic.description
    (vp,) = failing.viewpoints.values()
    assert vp.get_selected_guids() == ["2O2Fr$t4X7Zf8NOew3FLOH"]
    assert vp.visualization_info.perspective_camera is not None  # BCF 3.0 XSD requires a camera
    assert not topics[topic_guid("k-warn")].viewpoints  # project-level finding: nothing to select


def test_bcf_is_version_3_and_topic_guids_are_stable(tmp_path):
    body = render(REPORT, "bcf")
    (tmp_path / "b.bcf").write_bytes(body)
    with zipfile.ZipFile(tmp_path / "b.bcf") as z:
        assert 'VersionId="3.0"' in z.read("bcf.version").decode()
    assert set(_load(tmp_path, render(REPORT, "bcf")).topics) == set(_load(tmp_path, body).topics)


def test_camera_looks_at_the_element_origin(tmp_path):
    bcf = _load(tmp_path, render(REPORT, "bcf"))
    (vp,) = bcf.topics[topic_guid("k-fail")].viewpoints.values()
    cam = vp.visualization_info.perspective_camera
    pos = cam.camera_view_point
    d = cam.camera_direction
    # camera sits off the element and points straight at (10, 20, 3)
    to_target = (10.0 - pos.x, 20.0 - pos.y, 3.0 - pos.z)
    norm = sum(c * c for c in to_target) ** 0.5
    assert 3.0 < norm < 30.0  # close-up, not the 52 m origin overview
    assert (d.x, d.y, d.z) == pytest.approx(tuple(c / norm for c in to_target))


def test_issue_triage_travels_with_the_topic(tmp_path):
    issue = {"state": "in_progress", "assignee": "Dana", "due_date": "2026-12-01", "note": "fix in r3"}
    report = {**REPORT, "findings": [{**REPORT["findings"][0], "issue": issue}, REPORT["findings"][1]]}
    bcf = _load(tmp_path, render(report, "bcf"))  # keep the handle: topics read the zip lazily
    topics = bcf.topics
    t = topics[topic_guid("k-fail")].topic
    assert (t.topic_status, t.assigned_to) == ("In Progress", "Dana")
    assert str(t.due_date).startswith("2026-12-01")
    assert [c.comment for c in topics[topic_guid("k-fail")].comments] == ["fix in r3"]
    assert topics[topic_guid("k-warn")].topic.topic_status == "Open"  # untriaged stays open


def test_report_findings_carry_issue_triage(client, ifc_path):  # noqa: F811
    c = client
    mid = _model(c)
    aid = _upload(c, mid, ifc_path("rev1"))["result"]["audit_run_id"]
    key = c.get(f"{V1}/audits/{aid}/findings").json()[0]["identity_key"]
    c.put(f"{V1}/models/{mid}/issues", json={"identity_keys": [key], "assignee": "Dana"})
    csv_text = c.post(f"{V1}/audits/{aid}/reports", params={"format": "csv"}).text
    header, *rows = csv_text.splitlines()
    assert header.endswith("state,assignee,due_date,note")
    assert sum(",open,Dana,," in r for r in rows) == 1
    findings = c.post(f"{V1}/audits/{aid}/reports", params={"format": "json"}).json()["findings"]
    [hist] = [f["history"] for f in findings if f["identity_key"] == key]
    assert [(h["field"], h["new"]) for h in hist] == [("assignee", "Dana")]


def test_extensions_declare_every_value_the_topics_use(tmp_path):
    issue = {"state": "disputed", "assignee": "Dana"}
    report = {**REPORT, "findings": [{**REPORT["findings"][0], "issue": issue}, REPORT["findings"][1]]}
    bcf = _load(tmp_path, render(report, "bcf"))
    ext = bcf.extensions
    assert ext.topic_statuses.topic_status == ["Open", "In Progress", "Disputed", "Accepted", "Closed"]
    for handler in bcf.topics.values():
        t = handler.topic
        assert t.topic_type in ext.topic_types.topic_type
        assert t.priority in ext.priorities.priority
        assert set(t.labels.label) <= set(ext.topic_labels.topic_label)
    assert ext.users.user == ["Dana"]


def test_issue_history_becomes_dated_comments_by_their_author(tmp_path):
    history = [
        {
            "field": "state",
            "old": "open",
            "new": "disputed",
            "author": "Dana",
            "at": "2026-11-10T09:00:00+00:00",
        },
        {"field": "assignee", "old": None, "new": "Arman", "author": None, "at": "2026-11-10T10:00:00+00:00"},
    ]
    f = {**REPORT["findings"][0], "issue": {"state": "disputed", "note": "by design"}, "history": history}
    bcf = _load(tmp_path, render({**REPORT, "findings": [f]}, "bcf"))
    comments = bcf.topics[topic_guid("k-fail")].comments
    assert [(c.author, c.comment) for c in comments] == [
        ("Dana", "State: Open → Disputed"),
        ("Axiom BIM", "Assignee: — → Arman"),
        ("Axiom BIM", "by design"),
    ]
    assert str(comments[0].date).startswith("2026-11-10T09:00")


def _load21(tmp_path, body: bytes) -> BcfXml21:
    path = tmp_path / "a21.bcf"
    path.write_bytes(body)
    return BcfXml21.load(path)


REVIT = {
    **REPORT,
    "findings": [{**REPORT["findings"][0], "authoring_tool_id": "348812"}, REPORT["findings"][1]],
}


def test_bcf21_for_revit_addins_keeps_topics_viewpoints_and_triage(tmp_path):
    # most Revit BCF add-ins and Autodesk Construction Cloud import BCF 2.1, not 3.0
    issue = {"state": "in_progress", "assignee": "Dana", "note": "fix in r3"}
    report = {**REVIT, "findings": [{**REVIT["findings"][0], "issue": issue}, REVIT["findings"][1]]}
    body = render(report, "bcf21")
    (tmp_path / "v.bcf").write_bytes(body)
    with zipfile.ZipFile(tmp_path / "v.bcf") as z:
        assert 'VersionId="2.1"' in z.read("bcf.version").decode()
    bcf = _load21(tmp_path, body)
    topics = bcf.topics
    assert set(topics) == {topic_guid("k-fail"), topic_guid("k-warn")}  # same GUIDs as the 3.0 export
    failing = topics[topic_guid("k-fail")]
    t = failing.topic
    assert (t.topic_status, t.assigned_to, t.priority) == ("In Progress", "Dana", "high")
    assert t.labels == ["MAT-001", "completeness"]
    assert [c.comment for c in failing.comments] == ["fix in r3"]
    (vp,) = failing.viewpoints.values()
    (component,) = vp.visualization_info.components.selection.component
    assert (component.ifc_guid, component.authoring_tool_id) == ("2O2Fr$t4X7Zf8NOew3FLOH", "348812")
    assert vp.visualization_info.perspective_camera is not None


def test_bcf3_component_carries_the_revit_element_id(tmp_path):
    bcf = _load(tmp_path, render(REVIT, "bcf"))
    (vp,) = bcf.topics[topic_guid("k-fail")].viewpoints.values()
    (component,) = vp.visualization_info.components.selection.component
    assert component.authoring_tool_id == "348812"


def test_api_serves_bcf21_as_a_bcf_file(client, ifc_path):  # noqa: F811
    aid = _upload(client, _model(client), ifc_path("rev1"))["result"]["audit_run_id"]
    r = client.post(f"{V1}/audits/{aid}/reports", params={"format": "bcf21"})
    assert r.content.startswith(b"PK") and r.headers["content-disposition"].endswith('.bcf"')
