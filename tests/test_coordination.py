"""Cross-model consistency inside a project and the project-level delivery decision (D-39, audit gap G5)."""

from axiom.coordination import ModelFacts, check, worst_decision
from tests.test_api import V1, _upload, client  # noqa: F401 - client is a fixture

ARCH = ModelFacts("ARCH", "METRE", {"crs": "EPSG:32642", "eastings": 1.0}, (("L0", 0.0), ("L1", 3.0)))


def _by_check(models):
    return {c["check"]: c for c in check(models)}


def test_one_model_cannot_be_compared_so_nothing_passes():
    assert {c["status"] for c in check([ARCH])} == {"not_evaluated"}


def test_identical_models_pass_every_check():
    twin = ModelFacts("STR", ARCH.length_unit, ARCH.georef, (("Level 0", 0.004), ("Level 1", 3.0)))
    assert {c["status"] for c in check([ARCH, twin])} == {"pass"}  # 4 mm apart is the same storey


def test_differences_are_named_per_model_and_missing_georef_is_not_a_pass():
    mm = ModelFacts("MEP", "MILLIMETRE", None, (("L0", 0.0), ("L1", 3.2)))
    got = _by_check([ARCH, mm])
    assert got["length_unit"]["status"] == "fail"
    assert got["length_unit"]["actual"] == {"ARCH": "METRE", "MEP": "MILLIMETRE"}
    assert got["georeferencing"]["status"] == "fail" and got["georeferencing"]["actual"]["MEP"] is None
    assert got["storey_elevations"]["status"] == "warning"
    assert got["storey_elevations"]["actual"] == {"ARCH": [3.0], "MEP": [3.2]}  # only the unmatched levels
    none = ModelFacts("STR", "METRE", None, ())
    got = _by_check([none, ModelFacts("MEP", "METRE", None, ())])
    assert got["georeferencing"]["status"] == got["storey_elevations"]["status"] == "not_evaluated"


def test_project_decision_is_the_worst_model_decision_and_unaudited_models_leave_it_undecided():
    assert worst_decision(["accepted", "accepted_with_comments"]) == "accepted_with_comments"
    assert worst_decision(["accepted", "rejected", "undecided"]) == "rejected"
    assert worst_decision(["accepted", None]) == "undecided"
    assert worst_decision([]) == "undecided"


def test_coordination_endpoint_compares_the_latest_revision_of_each_model(client, ifc_path):  # noqa: F811
    c = client
    pid = c.post(f"{V1}/projects", json={"name": "Demo"}).json()["id"]
    arch = c.post(f"{V1}/projects/{pid}/models", json={"name": "ARCH"}).json()["id"]
    mep = c.post(f"{V1}/projects/{pid}/models", json={"name": "MEP"}).json()["id"]
    c.post(f"{V1}/projects/{pid}/models", json={"name": "Empty"})
    _upload(c, arch, ifc_path("clean"))
    _upload(c, mep, ifc_path("weird_units"))

    d = c.get(f"{V1}/projects/{pid}/coordination").json()
    assert [(m["name"], m["seq"]) for m in d["models"]] == [("ARCH", 1), ("MEP", 1), ("Empty", None)]
    assert d["decision"] == "undecided"  # no IDS checked, and one model has no delivery at all
    checks = {k["check"]: k for k in d["checks"]}
    assert checks["length_unit"]["status"] == "fail"
    assert checks["length_unit"]["actual"] == {"ARCH": "METRE", "MEP": "MILLIMETRE"}
    assert checks["storey_elevations"]["status"] == "pass"
    assert c.get(f"{V1}/projects/999/coordination").status_code == 404
