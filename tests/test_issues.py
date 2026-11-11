"""Issue triage on findings: state/assignee/due date keyed by the stable finding identity (D-32)."""

from tests.test_api import V1, _model, client  # noqa: F401 - client is a fixture

K1, K2 = "a" * 40, "b" * 40


def test_bulk_upsert_sets_only_the_given_fields(client):  # noqa: F811
    mid = _model(client)
    assert client.get(f"{V1}/models/{mid}/issues").json() == []
    r = client.put(
        f"{V1}/models/{mid}/issues",
        json={
            "identity_keys": [K1, K2],
            "state": "in_progress",
            "assignee": "Aigerim (MEP)",
            "due_date": "2026-12-01",
        },
    )
    assert r.status_code == 200, r.text
    client.put(
        f"{V1}/models/{mid}/issues", json={"identity_keys": [K2], "state": "disputed", "note": "by design"}
    )
    issues = {i["identity_key"]: i for i in client.get(f"{V1}/models/{mid}/issues").json()}
    assert issues[K1]["state"] == "in_progress" and issues[K1]["note"] is None
    assert issues[K2] | {"updated_at": None} == {
        "identity_key": K2,
        "state": "disputed",
        "assignee": "Aigerim (MEP)",
        "due_date": "2026-12-01",
        "note": "by design",
        "updated_at": None,
    }


def test_clearing_a_field_with_null(client):  # noqa: F811
    mid = _model(client)
    client.put(f"{V1}/models/{mid}/issues", json={"identity_keys": [K1], "assignee": "Dana"})
    client.put(f"{V1}/models/{mid}/issues", json={"identity_keys": [K1], "assignee": None})
    assert client.get(f"{V1}/models/{mid}/issues").json()[0]["assignee"] is None


def test_validation_and_unknown_model(client):  # noqa: F811
    mid = _model(client)
    put = lambda body, m=mid: client.put(f"{V1}/models/{m}/issues", json=body)  # noqa: E731
    assert (
        put({"identity_keys": [K1], "state": "resolved"}).status_code == 422
    )  # event word, not a triage state
    assert put({"identity_keys": ["not-a-key"], "state": "open"}).status_code == 422
    assert put({"identity_keys": [], "state": "open"}).status_code == 422
    assert put({"identity_keys": [K1], "state": "open"}, m=999).status_code == 404
    assert client.get(f"{V1}/models/999/issues").status_code == 404


def test_get_model_by_id(client):  # noqa: F811
    mid = _model(client)
    assert client.get(f"{V1}/models/{mid}").json()["name"] == "Structure"
    assert client.get(f"{V1}/models/999").status_code == 404


def test_every_change_is_recorded_with_old_and_new_value_and_the_entered_author(client):  # noqa: F811
    mid = _model(client)
    put = lambda **kw: client.put(f"{V1}/models/{mid}/issues", json={"identity_keys": [K1], **kw})  # noqa: E731
    put(assignee="Dana", due_date="2026-12-01", author="Ayan (client)")
    put(assignee="Dana", state="disputed", note="by design")  # assignee unchanged -> no event
    put(due_date=None)

    h = client.get(f"{V1}/models/{mid}/issues/{K1}/history").json()
    assert [(e["field"], e["old"], e["new"], e["author"]) for e in h] == [
        ("assignee", None, "Dana", "Ayan (client)"),
        ("due_date", None, "2026-12-01", "Ayan (client)"),
        ("state", "open", "disputed", None),
        ("note", None, "by design", None),
        ("due_date", "2026-12-01", None, None),
    ]
    assert all(e["at"] for e in h)
    assert client.get(f"{V1}/models/{mid}/issues/{K2}/history").json() == []
    assert client.get(f"{V1}/models/999/issues/{K1}/history").status_code == 404
