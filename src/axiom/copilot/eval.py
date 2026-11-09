"""Copilot eval: `uv run python -m axiom.copilot.eval` (repo root; needs ANTHROPIC_ or OPENROUTER_API_KEY).

Seeds a throwaway project from the test fixtures (rev1..rev3 + an injection model), asks every question in
tests/copilot/evals.yaml and grades deterministically: tools called, ids cited, phrases present/forbidden,
and zero unverified citations. Billed: each run makes ~25 agent loops.
"""

from __future__ import annotations

import logging
import re
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml
from sqlalchemy import Engine

from axiom.services import audits, comparisons, projects, revisions

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[3]
EVALS = ROOT / "tests" / "copilot" / "evals.yaml"
IDS = ROOT / "examples" / "ids" / "structural-basic.ids"
PASS_TARGET = 0.9


@dataclass(frozen=True)
class SeededProject:
    project_id: int
    revisions: dict[str, int]  # fixture name -> revision id


def seed_project(engine: Engine, files_dir: Path, ifc_path: Callable[[str], Path]) -> SeededProject:
    """Same pipeline as an upload (ingest → audit with IDS → compare with previous), run in-process."""
    pid = projects.create_project(engine, "Revision Tower")
    revs: dict[str, int] = {}
    for model, names in (("Structure", ("rev1", "rev2", "rev3")), ("Injection", ("injection",))):
        mid = projects.create_model(engine, pid, model)
        for name in names:
            rid = revisions.ingest(engine, mid, ifc_path(name), files_dir=files_dir).revision_id
            audits.run_audit(engine, rid, ids_path=IDS, files_dir=files_dir)
            comparisons.compare_with_previous(engine, rid)
            revs[name] = rid
    return SeededProject(pid, revs)


def grade(case: dict, answer: dict, guid: Callable[[str], str]) -> list[str]:
    """Failure reasons for one case; empty means pass. `answer` is agent.Answer as a dict."""
    text, fails = answer["answer"], []
    called = {c["name"] for c in answer["tool_calls"]}
    fails += [f"tool not called: {t}" for t in case.get("expect_tools", []) if t not in called]
    cited = {c["id"] for c in answer["citations"]}
    labels = {c["label"] for c in answer["citations"] if c["type"] == "finding"}
    fails += [f"element not cited: {n}" for n in case.get("must_cite", []) if guid(n) not in cited]
    fails += [f"finding not cited: {f}" for f in case.get("must_cite_findings", []) if f not in labels]
    fails += [f"missing phrase: {p}" for p in case.get("must_mention", []) if not re.search(p, text, re.I)]
    fails += [f"forbidden claim: {p}" for p in case.get("must_not_mention", []) if re.search(p, text, re.I)]
    if answer["unverified"]:
        fails.append(f"fabricated citations: {answer['unverified']}")
    return fails


def main(only: frozenset[str] = frozenset()) -> int:
    from axiom.copilot.agent import has_credentials  # noqa: PLC0415

    if not has_credentials():
        log.warning("no ANTHROPIC_API_KEY or OPENROUTER_API_KEY; copilot eval skipped")
        return 0
    from axiom.copilot.agent import ask, client_from_env  # noqa: PLC0415 - SDK only needed for a live run
    from axiom.copilot.tools import Scope  # noqa: PLC0415
    from axiom.repo.db import get_engine, migrate  # noqa: PLC0415
    from tests.fixtures.factory import build_fixture, stable_guid  # noqa: PLC0415 - fixtures live in tests/

    cases = [c for c in yaml.safe_load(EVALS.read_text()) if not only or c["id"].split("-")[0] in only]
    with tempfile.TemporaryDirectory() as tmp:
        engine = get_engine(f"sqlite:///{Path(tmp) / 'eval.db'}")
        migrate(engine)
        seeded = seed_project(engine, Path(tmp) / "files", lambda n: build_fixture(n, Path(tmp)))
        scope, client = Scope(engine, seeded.project_id), client_from_env()
        results, not_run = run_cases(
            cases, lambda c: ask(client, scope, c["question"]).as_dict(), stable_guid
        )
    return _report(results, not_run)


Result = tuple[str, list[str], dict]


def run_cases(
    cases: list[dict], answer: Callable[[dict], dict], guid: Callable[[str], str]
) -> tuple[list[Result], list[str]]:
    """Grade each case; on a provider rate limit stop and return the ids not run (free tiers cap per day)."""
    import anthropic  # noqa: PLC0415

    results: list[Result] = []
    for i, case in enumerate(cases):
        try:
            a = answer(case)
        except anthropic.RateLimitError as e:
            log.warning("rate limited at %s, stopping: %s", case["id"], e.message)
            return results, [c["id"] for c in cases[i:]]
        fails = grade(case, a, guid)
        results.append((case["id"], fails, a))
        log.info("%s %s %s", "PASS" if not fails else "FAIL", case["id"], "; ".join(fails))
    return results, []


def _report(results: list[Result], not_run: list[str] | None = None) -> int:
    passed = sum(1 for _, f, _ in results if not f)
    fabricated = sum(len(a["unverified"]) for _, _, a in results)
    rate = passed / len(results) if results else 0.0
    sys.stdout.write(
        f"\ncopilot eval: {passed}/{len(results)} passed ({rate:.0%}), fabricated citations: "
        f"{fabricated}, target ≥{PASS_TARGET:.0%} with 0 fabricated\n"
    )
    for cid, fails, _ in results:
        if fails:
            sys.stdout.write(f"  {cid}: {'; '.join(fails)}\n")
    if not_run:
        sys.stdout.write(f"  not run (rate limit): {','.join(c.split('-')[0] for c in not_run)}\n")
    return 0 if rate >= PASS_TARGET and fabricated == 0 and not not_run else 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # batches keep free tiers under their daily request caps: --only q01,q02
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else []
    sys.exit(main(frozenset(only)))
