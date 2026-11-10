from types import SimpleNamespace as NS

import pytest
from fastapi.testclient import TestClient

from axiom.api import create_app
from axiom.config import Settings
from axiom.copilot import agent
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
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
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


def test_openrouter_key_enables_copilot_with_free_default_model(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("AXIOM_COPILOT_MODEL", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-not-a-key")
    body = client.get(f"{V1}/copilot").json()
    assert body["available"] is True and body["model"].endswith(":free")
    sdk = agent.client_from_env()
    assert str(sdk.base_url).startswith("https://openrouter.ai/api")


def test_empty_model_env_falls_back_to_default(monkeypatch):
    # docker-compose passes unset vars as "" (AXIOM_COPILOT_MODEL=${AXIOM_COPILOT_MODEL:-})
    monkeypatch.setenv("AXIOM_COPILOT_MODEL", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-a-key")
    assert agent.model_name() == agent.DEFAULT_MODEL


def test_query_rate_limit_returns_429_and_window_frees_up(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-a-key")
    now = [0.0]
    monkeypatch.setattr(copilot, "LIMIT", copilot.Limiter(per_window=10, window_s=60.0, clock=lambda: now[0]))
    monkeypatch.setattr(copilot, "_client", lambda: None)
    monkeypatch.setattr(agent, "ask", lambda *_, **__: agent.Answer("ok", (), (), (), "end_turn"))
    pid = client.post(f"{V1}/projects", json={"name": "P"}).json()["id"]
    ask = lambda: client.post(f"{V1}/copilot/query", json={"project_id": pid, "question": "q"})  # noqa: E731
    assert all(ask().status_code == 200 for _ in range(10))
    r = ask()
    assert r.status_code == 429 and r.json()["error"]["code"] == "copilot_busy"
    now[0] = 61.0
    assert ask().status_code == 200


def test_second_query_while_one_is_running_is_busy(monkeypatch):
    limiter = copilot.Limiter(per_window=10, window_s=60.0)
    with limiter.slot(), pytest.raises(copilot.CopilotBusyError), limiter.slot():
        pass
    with limiter.slot():  # released after the first finished
        pass


def test_query_accepts_history_and_rejects_too_long_history(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-a-key")
    fake = FakeClient(NS(stop_reason="end_turn", content=[NS(type="text", text="Still none.")]))
    monkeypatch.setattr(copilot, "_client", lambda: fake)
    pid = client.post(f"{V1}/projects", json={"name": "P"}).json()["id"]
    turn = {"question": "models?", "answer": "No models yet."}
    body = {"project_id": pid, "question": "and now?", "history": [turn]}
    r = client.post(f"{V1}/copilot/query", json=body)
    assert r.status_code == 200, r.text
    assert [m["role"] for m in fake.requests[0]["messages"]] == ["user", "assistant", "user"]
    too_long = {"project_id": pid, "question": "q", "history": [turn] * 11}
    assert client.post(f"{V1}/copilot/query", json=too_long).status_code == 422
