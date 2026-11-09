import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from axiom.api import create_app
from axiom.config import Settings
from axiom.services.jobs import KINDS
from tests.conftest import load_expected
from tests.jobkinds import TEST_KINDS

IDS = Path(__file__).parent.parent / "examples" / "ids" / "structural-basic.ids"
V1 = "/api/v1"


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        data_dir=tmp_path, db_url=f"sqlite:///{tmp_path / 'a.db'}", max_upload_mb=1, job_timeout_s=60
    )
    with TestClient(create_app(settings, kinds=KINDS | TEST_KINDS, poll_s=0.05)) as c:
        yield c


def _wait(c: TestClient, job_id: int) -> dict:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        job = c.get(f"{V1}/jobs/{job_id}").json()
        if job["status"] in ("done", "error"):
            return job
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} did not finish")


def _model(c: TestClient) -> int:
    project = c.post(f"{V1}/projects", json={"name": "Demo"}).json()
    return c.post(f"{V1}/projects/{project['id']}/models", json={"name": "Structure"}).json()["id"]


def _upload(c: TestClient, model_id: int, path: Path, ids_hash: str | None = None) -> dict:
    data = {"ids_hash": ids_hash} if ids_hash else {}
    with path.open("rb") as fh:
        r = c.post(f"{V1}/models/{model_id}/revisions", files={"file": (path.name, fh)}, data=data)
    assert r.status_code == 202, r.text
    return _wait(c, r.json()["job_id"])


def test_upload_two_revisions_then_browse_findings_and_comparison(client, ifc_path):
    c = client
    model_id = _model(c)
    with IDS.open("rb") as fh:
        ids_hash = c.post(f"{V1}/ids", files={"file": ("s.ids", fh)}).json()["ids_hash"]
    j1 = _upload(c, model_id, ifc_path("rev1"), ids_hash)
    j2 = _upload(c, model_id, ifc_path("rev2"), ids_hash)
    assert j1["status"] == j2["status"] == "done", (j1, j2)
    rev2 = j2["result"]["revision_id"]

    revs = c.get(f"{V1}/models/{model_id}/revisions").json()
    assert [r["seq"] for r in revs] == [1, 2]
    summary = c.get(f"{V1}/revisions/{rev2}").json()
    assert (
        summary["class_counts"]["IfcColumn"] == 4
        and summary["latest_audit_id"] == j2["result"]["audit_run_id"]
    )

    audit_id = j2["result"]["audit_run_id"]
    walls = c.get(f"{V1}/audits/{audit_id}/findings", params={"rule": "IDS:STR-WALL"}).json()
    assert all(f["rule_id"] == "IDS:STR-WALL" for f in walls)
    mhi = c.get(f"{V1}/audits/{audit_id}/health-index").json()
    assert 0 <= mhi["score"] <= 100

    comparison_id = j2["result"]["comparison_id"]
    expected = load_expected("revisions")["rev1_rev2"]
    changes = c.get(f"{V1}/comparisons/{comparison_id}/changes").json()
    names = {ch["global_id"]: ch for ch in changes}
    assert len([ch for ch in changes if ch["kind"] == "added"]) == len(expected["added"]) and names
    events = c.get(f"{V1}/comparisons/{comparison_id}/events").json()
    got = {(e["rule_id"], e["element_name"]): e["event"] for e in events if e["event"] != "persistent"}
    want = {
        (r, el): ev
        for key in ("events", "ids_events")
        for r, m in expected[key].items()
        for el, ev in m.items()
    }
    assert got == want

    rev1 = j1["result"]["revision_id"]
    r = c.post(f"{V1}/comparisons", json={"base_revision_id": rev1, "head_revision_id": rev2})
    job = _wait(c, r.json()["job_id"])
    assert job["status"] == "done"
    assert c.get(f"{V1}/comparisons/{job['result']['comparison_id']}").json()["head_revision_id"] == rev2


def test_elements_paginated_filtered_and_by_global_id(client, ifc_path):
    c = client
    rev = _upload(c, _model(c), ifc_path("clean"))["result"]["revision_id"]
    page = c.get(f"{V1}/revisions/{rev}/elements", params={"ifc_class": "IfcWall", "limit": 2}).json()
    assert page["total"] == 6 and len(page["items"]) == 2
    hit = c.get(f"{V1}/revisions/{rev}/elements", params={"search": "w1"}).json()
    assert [e["name"] for e in hit["items"]] == ["W1"]
    gid = hit["items"][0]["global_id"]
    el = c.get(f"{V1}/revisions/{rev}/elements/{gid}").json()
    assert el["name"] == "W1" and el["quantities"]
    assert c.get(f"{V1}/revisions/{rev}/elements/nope").status_code == 404
    q = c.get(f"{V1}/revisions/{rev}/quantities", params={"by": "class"}).json()
    assert any(r["group"] == "IfcWall" and r["unit"] == "m3" for r in q["rows"])


def test_serves_stored_ifc_and_spatial_tree(client, ifc_path):
    c = client
    src = ifc_path("clean")
    rev = _upload(c, _model(c), src)["result"]["revision_id"]
    f = c.get(f"{V1}/revisions/{rev}/file")
    assert f.status_code == 200 and f.content == src.read_bytes()
    assert f.headers["cache-control"] == "private, max-age=31536000, immutable"  # content-addressed
    tree = c.get(f"{V1}/revisions/{rev}/tree").json()
    storeys = [n["name"] for n in tree["nodes"] if n["ifc_class"] == "IfcBuildingStorey"]
    assert storeys == ["Level 0", "Level 1"]
    ids = {n["global_id"] for n in tree["nodes"]}
    assert len(tree["elements"]) == 16 and all(e["container_global_id"] in ids for e in tree["elements"])
    assert c.get(f"{V1}/revisions/999/file").status_code == 404
    assert c.get(f"{V1}/revisions/999/tree").status_code == 404


def test_rejects_non_ifc_oversized_and_bad_ids(client, tmp_path):
    c = client
    model_id = _model(c)
    fake = tmp_path / "x.ifc"
    fake.write_text("hello")
    with fake.open("rb") as fh:
        r = c.post(f"{V1}/models/{model_id}/revisions", files={"file": ("x.ifc", fh)})
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_request"
    assert str(tmp_path) not in r.text
    big = tmp_path / "big.ifc"
    big.write_bytes(b"ISO-10303-21;\n" + b"x" * (2 * 1024 * 1024))
    with big.open("rb") as fh:
        r = c.post(f"{V1}/models/{model_id}/revisions", files={"file": ("big.ifc", fh)})
    assert r.status_code == 413
    r = c.post(f"{V1}/models/{model_id}/revisions", files={"file": ("x.txt", b"ISO-10303-21;")})
    assert r.status_code == 400
    for body in (b"<ids/>", b"not xml <<"):
        r = c.post(f"{V1}/ids", files={"file": ("bad.ids", body)})
        assert r.status_code == 400 and ".part" not in r.text
    assert c.get(f"{V1}/models/999/revisions").status_code == 404
    assert c.get(f"{V1}/jobs/999").json()["error"]["code"] == "not_found"


def test_crashing_job_leaves_api_up(client):
    c = client
    app = c.app
    job_id = app.state.enqueue("abort", {})
    assert _wait(c, job_id)["status"] == "error"
    assert c.get(f"{V1}/projects").status_code == 200
