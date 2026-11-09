"""buildingSMART IDS test cases: the adapter's verdict must match the suite's pass-/fail- prefix."""

from pathlib import Path

import pytest

from axiom.ids import run_ids

CASES = sorted((Path(__file__).parent / "fixtures" / "ids" / "conformance").glob("*.ids"))
# Known IfcTester 0.9.0 deviations. We report IfcTester's verdict as-is (never reinterpret); strict xfail
# flags the day an upgrade fixes them.
UPSTREAM_BUGS = {
    "attribute__pass-an_optional_attribute_passes_if_null": "IfcTester 0.9.0 fails optional null"
}


def _case(p: Path):
    bug = UPSTREAM_BUGS.get(p.stem)
    return pytest.param(p, id=p.stem, marks=[pytest.mark.xfail(strict=True, reason=bug)] if bug else [])


@pytest.mark.parametrize("ids_path", [_case(p) for p in CASES])
def test_adapter_matches_suite_outcome(ids_path):
    expected = ids_path.stem.split("__", 1)[1].split("-", 1)[0]
    out = run_ids(ids_path.with_suffix(".ifc"), ids_path, model_id=1)
    failed = any(f.status == "fail" for f in out.findings)
    assert ("fail" if failed else "pass") == expected, [f.message for f in out.findings]


def test_subset_covers_every_facet_with_both_outcomes():
    seen = {(p.stem.split("__")[0], p.stem.split("__")[1].split("-")[0]) for p in CASES}
    facets = {"entity", "attribute", "material", "classification", "partof", "property"}
    assert seen == {(f, o) for f in facets for o in ("pass", "fail")}
