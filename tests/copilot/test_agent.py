import json
from types import SimpleNamespace as NS

from axiom.copilot.agent import SYSTEM, ask
from axiom.copilot.tools import Scope
from tests.fixtures.factory import INJECTION_TEXT, stable_guid

FAKE = "0000000000000000000000"


def text(t: str) -> NS:
    return NS(type="text", text=t)


def tool(name: str, args: dict, id_: str = "t1") -> NS:
    return NS(type="tool_use", id=id_, name=name, input=args)


class FakeClient:
    """Plays scripted responses and records every request."""

    def __init__(self, *responses: NS):
        self.responses, self.requests = list(responses), []
        self.messages = self

    def create(self, **kw):
        self.requests.append(kw | {"messages": list(kw["messages"])})
        return self.responses.pop(0)


def reply(stop: str, *content: NS) -> NS:
    return NS(stop_reason=stop, content=list(content))


def _findings_args(seeded, rev: str) -> dict:
    return {
        "revision_id": seeded.project.revisions[rev],
        "status": "fail",
        "severity": None,
        "rule_id": "MAT-001",
        "limit": 20,
        "offset": 0,
    }


def test_cited_ids_from_tool_results_become_citations(seeded):
    c2 = stable_guid("C2")
    client = FakeClient(
        reply("tool_use", tool("findings", _findings_args(seeded, "rev3"))),
        reply("end_turn", text(f"In r3, C2 [[el:{c2}]] has no material (MAT-001).")),
    )
    out = ask(client, Scope(seeded.engine, seeded.project.project_id), "missing material in r3?")
    assert out.unverified == ()
    assert [(c.type, c.id, c.label) for c in out.citations] == [("element", c2, "C2")]
    assert out.citations[0].revision_id == seeded.project.revisions["rev3"]
    assert [t["name"] for t in out.tool_calls] == ["findings"]
    result = client.requests[1]["messages"][-1]["content"][0]
    assert result["type"] == "tool_result" and result["tool_use_id"] == "t1" and "is_error" not in result


def test_fabricated_id_triggers_one_retry_then_is_stripped_and_flagged(seeded):
    client = FakeClient(
        reply("end_turn", text(f"Element [[el:{FAKE}]] is the problem.")),
        reply("end_turn", text(f"Still [[el:{FAKE}]].")),
    )
    out = ask(client, Scope(seeded.engine, seeded.project.project_id), "which element?")
    assert len(client.requests) == 2
    retry = client.requests[1]["messages"][-1]
    assert retry["role"] == "user" and FAKE in retry["content"]
    assert out.unverified == (FAKE,)
    assert FAKE not in out.answer and "unverified" in out.answer
    assert out.citations == ()


def test_retry_that_fixes_the_citation_passes(seeded):
    c2 = stable_guid("C2")
    client = FakeClient(
        reply("end_turn", text(f"See [[el:{FAKE}]].")),
        reply("tool_use", tool("findings", _findings_args(seeded, "rev3"))),
        reply("end_turn", text(f"C2 [[el:{c2}]].")),
    )
    out = ask(client, Scope(seeded.engine, seeded.project.project_id), "which?")
    assert out.unverified == () and [c.id for c in out.citations] == [c2]


def test_bare_guid_in_prose_is_checked_too(seeded):
    client = FakeClient(
        reply("end_turn", text("Look at 3fZ9k2LmQx0aB7cD1eF2gH.")), reply("end_turn", text("ok"))
    )
    out = ask(client, Scope(seeded.engine, seeded.project.project_id), "?")
    assert len(client.requests) == 2 and out.unverified == ()


def test_tool_error_goes_back_as_is_error(seeded):
    client = FakeClient(
        reply("tool_use", tool("mhi", {"revision_id": 999_999})),
        reply("end_turn", text("Not available.")),
    )
    ask(client, Scope(seeded.engine, seeded.project.project_id), "mhi?")
    result = client.requests[1]["messages"][-1]["content"][0]
    assert result["is_error"] is True and "not found" in result["content"]


def test_refusal_and_round_limit(seeded):
    scope = Scope(seeded.engine, seeded.project.project_id)
    refused = ask(FakeClient(reply("refusal")), scope, "?")
    assert refused.stop_reason == "refusal" and "declined" in refused.answer
    loop = FakeClient(*[reply("tool_use", tool("project_summary", {}, f"t{i}")) for i in range(3)])
    capped = ask(loop, scope, "?", max_rounds=3)
    assert capped.stop_reason == "max_rounds" and len(loop.requests) == 3


def test_injection_text_reaches_the_model_only_as_data(seeded):
    w2 = stable_guid("W2")
    args = {"revision_id": seeded.project.revisions["injection"], "global_id": w2}
    client = FakeClient(
        reply("tool_use", tool("element_detail", args)), reply("end_turn", text(f"W2 [[el:{w2}]]."))
    )
    ask(client, Scope(seeded.engine, seeded.project.project_id), "what is W2?")
    content = client.requests[1]["messages"][-1]["content"][0]["content"]
    assert json.loads(content)["data"]["name"] == INJECTION_TEXT
    assert "never instructions" in SYSTEM.lower() or "never as instructions" in SYSTEM.lower()
