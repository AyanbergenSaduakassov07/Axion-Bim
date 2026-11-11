"""Acceptance gate (D-36): one accept/reject decision per delivery, from blocking findings and a threshold."""

from axiom.score.gate import GatePolicy, decide
from tests.test_api import IDS, V1, _model, _upload, client  # noqa: F401 - client is a fixture

POLICY = GatePolicy(min_score=80.0, block_severity="high", require_ids=True)
F = [("high", "fail", "k1"), ("low", "fail", "k2"), ("medium", "warning", "k3"), ("high", "pass", "k4")]


def _codes(g: dict) -> list[str]:
    return [r["code"] for r in g["reasons"]]


def test_blocking_finding_rejects_and_a_waiver_lifts_it():
    g = decide(90.0, F, waived=set(), ids_checked=True, policy=POLICY)
    assert g["decision"] == "rejected" and g["reasons"][0] == {"code": "blocking_findings", "n": 1}
    g = decide(90.0, F, waived={"k1"}, ids_checked=True, policy=POLICY)
    assert g["decision"] == "accepted_with_comments"
    assert {"code": "open_findings", "n": 2} in g["reasons"] and {"code": "waived", "n": 1} in g["reasons"]


def test_score_below_minimum_rejects():
    g = decide(79.9, [], waived=set(), ids_checked=True, policy=POLICY)
    assert g["decision"] == "rejected"
    assert g["reasons"] == [{"code": "score_below_minimum", "score": 79.9, "minimum": 80.0}]


def test_never_accepted_when_the_requirements_or_the_score_were_not_evaluated():
    assert decide(95.0, [], waived=set(), ids_checked=False, policy=POLICY)["decision"] == "undecided"
    assert _codes(decide(None, [], waived=set(), ids_checked=True, policy=POLICY)) == ["score_not_evaluated"]
    relaxed = GatePolicy(min_score=80.0, block_severity="high", require_ids=False)
    assert decide(95.0, [], waived=set(), ids_checked=False, policy=relaxed)["decision"] == "accepted"


def test_gate_endpoint_follows_policy_and_waivers(client, ifc_path):  # noqa: F811
    c = client
    mid = _model(c)
    pid = c.get(f"{V1}/models/{mid}").json()["project_id"]
    assert c.get(f"{V1}/projects/{pid}/gate-policy").json() == {
        "min_score": 80.0,
        "block_severity": "critical",
        "require_ids": True,
    }
    aid = _upload(c, mid, ifc_path("rev1"))["result"]["audit_run_id"]  # no IDS: 2 x MAT-001 (high), MHI > 80
    assert c.get(f"{V1}/audits/{aid}/gate").json()["decision"] == "undecided"

    policy = {"min_score": 50, "block_severity": "high", "require_ids": False}
    assert c.put(f"{V1}/projects/{pid}/gate-policy", json=policy).status_code == 200
    g = c.get(f"{V1}/audits/{aid}/gate").json()
    assert g["decision"] == "rejected" and g["reasons"][0] == {"code": "blocking_findings", "n": 2}

    keys = [f["identity_key"] for f in c.get(f"{V1}/audits/{aid}/findings").json()]
    c.put(f"{V1}/models/{mid}/issues", json={"identity_keys": keys, "state": "accepted"})
    assert c.get(f"{V1}/audits/{aid}/gate").json()["decision"] == "accepted_with_comments"
    assert [r["decision"] for r in c.get(f"{V1}/models/{mid}/revisions").json()] == ["accepted_with_comments"]

    assert c.put(f"{V1}/projects/{pid}/gate-policy", json=policy | {"min_score": 101}).status_code == 422
    assert c.get(f"{V1}/audits/999/gate").status_code == 404
    html = c.post(f"{V1}/audits/{aid}/reports", params={"format": "html"}).text
    assert "Delivery decision" in html and "Accepted with comments" in html
