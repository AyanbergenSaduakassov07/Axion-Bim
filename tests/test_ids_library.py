"""Project IDS library: requirement files stored once per project, one marked default (D-34)."""

from tests.test_api import IDS, V1, _model, client  # noqa: F401 - client is a fixture


def _add(c, pid: int, name: str = "Client EIR v1"):
    with IDS.open("rb") as fh:
        return c.post(f"{V1}/projects/{pid}/ids", files={"file": ("s.ids", fh)}, data={"name": name})


def _project(c) -> int:
    mid = _model(c)
    return c.get(f"{V1}/models/{mid}").json()["project_id"]


def test_first_file_becomes_default_and_same_file_is_not_duplicated(client):  # noqa: F811
    pid = _project(client)
    r = _add(client, pid)
    assert r.status_code == 201, r.text
    entry = r.json()
    assert entry["name"] == "Client EIR v1" and entry["is_default"] and len(entry["ids_hash"]) == 64
    assert _add(client, pid, "again").json()["id"] == entry["id"]
    assert [e["id"] for e in client.get(f"{V1}/projects/{pid}/ids").json()] == [entry["id"]]


def test_set_default_and_unknown_ids(client):  # noqa: F811
    pid = _project(client)
    eid = _add(client, pid).json()["id"]
    r = client.put(f"{V1}/projects/{pid}/ids/{eid}/default", json={"is_default": False})
    assert r.status_code == 200 and r.json()[0]["is_default"] is False
    client.put(f"{V1}/projects/{pid}/ids/{eid}/default", json={"is_default": True})
    assert client.get(f"{V1}/projects/{pid}/ids").json()[0]["is_default"] is True
    assert client.put(f"{V1}/projects/{pid}/ids/999/default", json={"is_default": True}).status_code == 404
    assert client.get(f"{V1}/projects/999/ids").status_code == 404


def test_rejects_invalid_ids_file(client):  # noqa: F811
    pid = _project(client)
    r = client.post(
        f"{V1}/projects/{pid}/ids", files={"file": ("bad.ids", b"<not-ids/>")}, data={"name": "x"}
    )
    assert r.status_code in (400, 422)
