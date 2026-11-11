"""Frozen acceptance certificate: the gate decision of one audit, as issued, with a content hash (D-42)."""

from axiom.certificate import digest, verify
from tests.test_api import V1, _model, _upload, client  # noqa: F401 - client is a fixture


def test_digest_is_stable_and_any_edit_breaks_verification():
    payload = {"decision": "accepted", "reasons": [], "file_sha256": "ab" * 32, "issued_by": "Ayan"}
    same = dict(reversed(list(payload.items())))  # key order must not matter
    assert digest(payload) == digest(same) and len(digest(payload)) == 64
    assert verify(payload, digest(payload))
    assert not verify({**payload, "decision": "rejected"}, digest(payload))


def test_certificate_freezes_the_decision_even_after_the_policy_changes(client, ifc_path):  # noqa: F811
    c = client
    mid = _model(c)
    pid = c.get(f"{V1}/models/{mid}").json()["project_id"]
    c.put(
        f"{V1}/projects/{pid}/gate-policy",
        json={"min_score": 50, "block_severity": "critical", "require_ids": False},
    )
    aid = _upload(c, mid, ifc_path("rev1"))["result"]["audit_run_id"]

    r = c.post(f"{V1}/audits/{aid}/certificates", json={"issued_by": "Ayan (client BIM manager)"})
    assert r.status_code == 201, r.text
    cert = r.json()
    p = cert["payload"]
    assert p["decision"] == "accepted_with_comments" and p["issued_by"] == "Ayan (client BIM manager)"
    assert p["audit_run_id"] == aid and len(p["file_sha256"]) == 64 and p["ruleset_version"]
    assert p["policy"]["min_score"] == 50 and p["ids_hash"] is None and p["score"] is not None
    assert cert["valid"] is True and len(cert["sha256"]) == 64

    c.put(
        f"{V1}/projects/{pid}/gate-policy",
        json={"min_score": 99, "block_severity": "critical", "require_ids": False},
    )
    assert c.get(f"{V1}/audits/{aid}/gate").json()["decision"] == "rejected"  # live gate follows the policy
    (frozen,) = c.get(f"{V1}/audits/{aid}/certificates").json()
    assert frozen["payload"]["decision"] == "accepted_with_comments" and frozen["sha256"] == cert["sha256"]

    assert c.post(f"{V1}/audits/{aid}/certificates", json={"issued_by": ""}).status_code == 422
    assert c.post(f"{V1}/audits/999/certificates", json={"issued_by": "x"}).status_code == 404
