"""Project dashboard: MHI trend per model and issue KPIs on the latest audit (D-33)."""

from datetime import date

from axiom.services.dashboard import issue_tally
from tests.test_api import V1, _model, _upload, client  # noqa: F401 - client is a fixture

TODAY = date(2026, 11, 10)


def test_tally_counts_untriaged_as_open_and_flags_overdue():
    rows = [("k1", "MAT-001"), ("k2", "MAT-001"), ("k3", "QTO-001"), ("k4", "QTO-001")]
    issues = {
        "k2": ("in_progress", "Dana", date(2026, 11, 1)),  # overdue
        "k3": ("closed", "Dana", date(2026, 11, 1)),  # done, not overdue
        "k4": ("open", None, date(2026, 12, 1)),
    }
    t = issue_tally(rows, issues, TODAY)
    assert t["states"] == {"open": 2, "in_progress": 1, "disputed": 0, "accepted": 0, "closed": 1}
    assert t["overdue"] == 1 and t["unassigned"] == 2  # closed issues do not count as unassigned work
    assert t["by_assignee"] == [{"assignee": "Dana", "active": 1, "overdue": 1}]
    assert t["by_rule"] == [{"rule_id": "MAT-001", "active": 2}, {"rule_id": "QTO-001", "active": 1}]


def test_dashboard_endpoint(client, ifc_path):  # noqa: F811
    mid = _model(client)
    job = _upload(client, mid, ifc_path("rev1"))
    pid = client.get(f"{V1}/revisions/{job['result']['revision_id']}").json()["project_id"]
    findings = client.get(f"{V1}/audits/{job['result']['audit_run_id']}/findings").json()
    client.put(
        f"{V1}/models/{mid}/issues",
        json={"identity_keys": [findings[0]["identity_key"]], "assignee": "Dana", "due_date": "2020-01-01"},
    )

    d = client.get(f"{V1}/projects/{pid}/dashboard").json()
    (m,) = d["models"]
    assert m["model_id"] == mid and [p["seq"] for p in m["trend"]] == [1]
    assert 0 <= m["trend"][0]["score"] <= 100 and m["findings"] == len(findings)
    assert d["issues"]["states"]["open"] == len(findings) and d["issues"]["overdue"] == 1
    assert d["issues"]["by_assignee"] == [{"assignee": "Dana", "active": 1, "overdue": 1}]
    assert client.get(f"{V1}/projects/999/dashboard").status_code == 404


def test_overdue_uses_the_callers_timezone_and_rejects_unknown_ones(client):  # noqa: F811
    mid = _model(client)
    pid = client.get(f"{V1}/models/{mid}").json()["project_id"]
    assert client.get(f"{V1}/projects/{pid}/dashboard", params={"tz": "Asia/Almaty"}).status_code == 200
    assert client.get(f"{V1}/projects/{pid}/dashboard", params={"tz": "Mars/Olympus"}).status_code == 400


def test_revision_list_carries_the_latest_audit_score(client, ifc_path):  # noqa: F811
    mid = _model(client)
    job = _upload(client, mid, ifc_path("rev1"))
    (rev,) = client.get(f"{V1}/models/{mid}/revisions").json()
    (audit,) = client.get(f"{V1}/revisions/{job['result']['revision_id']}/audits").json()
    assert rev["score"] == audit["score"] and rev["blocked"] == audit["blocked"]
