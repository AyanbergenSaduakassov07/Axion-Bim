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
