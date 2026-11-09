"""BCF 3.0 export: one topic per open finding, element selected in a viewpoint, stable topic GUIDs."""

import zipfile

from bcf.v3.bcfxml import BcfXml

from axiom.report import render
from axiom.report.bcf import topic_guid


def _finding(status: str, gid: str | None, key: str) -> dict:
    return {
        "global_id": gid, "element_name": "C2", "ifc_class": "IfcColumn", "rule_id": "MAT-001",
        "rule_version": "1", "status": status, "severity": "high", "category": "material",
        "dimension": "completeness", "expected": "a material", "actual": "none",
        "message": "Element has no material", "identity_key": key, "evidence": {},
    }  # fmt: skip


REPORT = {
    "audit": {"id": 7, "revision": {"project_name": "Tower", "seq": 2}},
    "findings": [
        _finding("fail", "2O2Fr$t4X7Zf8NOew3FLOH", "k-fail"),
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
