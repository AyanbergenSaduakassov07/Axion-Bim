import yaml

from axiom.copilot.eval import EVALS, grade
from tests.fixtures.factory import CATALOGUE, EXTRA

KNOWN = {d.name for d in CATALOGUE} | set(EXTRA)
FIELDS = {
    "id",
    "question",
    "expect_tools",
    "must_cite",
    "must_cite_findings",
    "must_mention",
    "must_not_mention",
}


def test_eval_set_shape():
    cases = yaml.safe_load(EVALS.read_text())
    assert len(cases) == 25 and len({c["id"] for c in cases}) == 25
    for c in cases:
        assert set(c) <= FIELDS, c["id"]
        assert set(c.get("must_cite", [])) <= KNOWN, c["id"]
    ids = " ".join(c["id"] for c in cases)
    assert "unanswerable" in ids and "safety-bait" in ids and "injection" in ids


def _answer(text: str, **kw) -> dict:
    return {"answer": text, "citations": [], "tool_calls": [], "unverified": ()} | kw


def test_grade_reports_each_failure_kind():
    case = {
        "expect_tools": ["mhi"],
        "must_cite": ["C2"],
        "must_cite_findings": ["MAT-001 C2"],
        "must_mention": ["95"],
        "must_not_mention": ["unsafe"],
    }
    fails = grade(case, _answer("It is unsafe.", unverified=("X",)), lambda n: f"g-{n}")
    assert len(fails) == 6


def test_grade_passes_a_grounded_answer():
    case = {
        "expect_tools": ["mhi"],
        "must_cite": ["C2"],
        "must_cite_findings": ["MAT-001 C2"],
        "must_mention": ["95"],
    }
    answer = _answer(
        "MHI 95.2; C2 lacks material.",
        tool_calls=[{"name": "mhi", "input": {}}],
        citations=[
            {"type": "element", "id": "g-C2", "label": "C2"},
            {"type": "finding", "id": "k", "label": "MAT-001 C2"},
        ],
    )
    assert grade(case, answer, lambda n: f"g-{n}") == []


def test_rate_limit_stops_the_run_and_keeps_partial_results():
    import anthropic  # noqa: PLC0415
    import httpx  # noqa: PLC0415

    from axiom.copilot.eval import run_cases  # noqa: PLC0415

    def answer(case: dict) -> dict:
        if case["id"] == "q02":
            resp = httpx.Response(429, request=httpx.Request("POST", "https://example.invalid"))
            raise anthropic.RateLimitError("free-models-per-day", response=resp, body=None)
        return {"answer": "x", "citations": [], "tool_calls": [], "unverified": []}

    cases = [{"id": i, "question": "?"} for i in ("q01", "q02", "q03")]
    results, not_run = run_cases(cases, answer, lambda _: "")
    assert [cid for cid, _, _ in results] == ["q01"]
    assert not_run == ["q02", "q03"]


def test_provider_outage_skips_one_case_and_continues():
    import anthropic  # noqa: PLC0415
    import httpx  # noqa: PLC0415

    from axiom.copilot.eval import run_cases  # noqa: PLC0415

    def answer(case: dict) -> dict:
        if case["id"] == "q02":
            resp = httpx.Response(503, request=httpx.Request("POST", "https://example.invalid"))
            raise anthropic.InternalServerError("overloaded", response=resp, body=None)
        return {"answer": "x", "citations": [], "tool_calls": [], "unverified": []}

    cases = [{"id": i, "question": "?"} for i in ("q01", "q02", "q03")]
    results, not_run = run_cases(cases, answer, lambda _: "")
    assert [cid for cid, _, _ in results] == ["q01", "q03"]
    assert not_run == ["q02"]


def test_report_with_no_results_does_not_divide_by_zero(capsys):
    from axiom.copilot.eval import _report  # noqa: PLC0415

    assert _report([], not_run=["q01"]) == 1
    assert "not run" in capsys.readouterr().out
