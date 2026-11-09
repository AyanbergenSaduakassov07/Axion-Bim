from types import SimpleNamespace as NS

import pytest
from fastapi.testclient import TestClient

from axiom.api import create_app
from axiom.config import Settings
from axiom.services import copilot
from tests.copilot.test_agent import FakeClient

V1 = "/api/v1"


@pytest.fixture
def client(tmp_path):
    settings = Settings(data_dir=tmp_path, db_url=f"sqlite:///{tmp_path / 'a.db'}")
    with TestClient(create_app(settings, run_jobs=False)) as c:
        yield c


def test_without_key_copilot_is_hidden_and_returns_503(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert client.get(f"{V1}/copilot").json()["available"] is False
    pid = client.post(f"{V1}/projects", json={"name": "P"}).json()["id"]
    r = client.post(f"{V1}/copilot/query", json={"project_id": pid, "question": "hi"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "copilot_unavailable"
    assert client.get(f"{V1}/projects").status_code == 200  # everything else intact


def test_query_returns_answer_citations_and_tool_calls(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-a-key")
    fake = FakeClient(
        NS(stop_reason="tool_use", content=[NS(type="tool_use", id="t1", name="project_summary", input={})]),
        NS(stop_reason="end_turn", content=[NS(type="text", text="The project has no models yet.")]),
    )
    monkeypatch.setattr(copilot, "_client", lambda: fake)
    pid = client.post(f"{V1}/projects", json={"name": "P"}).json()["id"]
    r = client.post(f"{V1}/copilot/query", json={"project_id": pid, "question": "what is here?"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["answer"] == "The project has no models yet."
    assert body["tool_calls"] == [{"name": "project_summary", "input": {}}]
    assert body["citations"] == [] and body["unverified"] == []


def test_unknown_project_is_404_and_empty_question_422(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-a-key")
    assert client.post(f"{V1}/copilot/query", json={"project_id": 999, "question": "x"}).status_code == 404
    assert client.post(f"{V1}/copilot/query", json={"project_id": 1, "question": ""}).status_code == 422
