import pytest

from axiom.i18n import localize_finding, tr


@pytest.mark.parametrize(
    ("en", "ru"),
    [
        ("IfcBeam has no material assigned", "IfcBeam: не назначен материал"),
        ("IfcWall has no Name", "IfcWall: не заполнено имя (Name)"),
        ("IfcSlab has no classification reference", "IfcSlab: нет ссылки на классификатор"),
        ("IfcColumn has no base quantity set", "IfcColumn: нет базового набора количеств"),
        ("IfcDoor has no geometric representation", "IfcDoor: нет геометрического представления"),
        ("IfcWall is not located in any building storey", "IfcWall: не размещён ни на одном этаже"),
        (
            "GlobalId 2O2Fr$t4X7Zf8NOew3FLOH is shared by 3 elements",
            "GlobalId 2O2Fr$t4X7Zf8NOew3FLOH используется 3 элементами",
        ),
        (
            "declared volume disagrees with geometry; likely unit-scale error (x1000)",
            "заявленный объём расходится с геометрией; вероятна ошибка масштаба единиц (x1000)",
        ),
        ("container none", "контейнер отсутствует"),
        ("contained in a storey", "размещён на этаже"),
        ("2 elements", "элементов: 2"),
    ],
)
def test_translates_rule_texts(en, ru):
    assert tr("ru", en) == ru


def test_unknown_text_and_english_pass_through():
    assert tr("ru", "Pset_WallCommon.FireRating: missing") == "Pset_WallCommon.FireRating: missing"
    assert tr("en", "IfcBeam has no material assigned") == "IfcBeam has no material assigned"
    assert tr("ru", None) is None


def test_localize_finding_returns_a_copy_and_keeps_tokens():
    f = {
        "message": "IfcBeam has no material assigned",
        "expected": "material association",
        "actual": "none",
        "status": "fail",
    }
    out = localize_finding(f, "ru")
    assert (
        out["message"] == "IfcBeam: не назначен материал"
        and out["actual"] == "нет"
        and out["status"] == "fail"
    )
    assert f["actual"] == "none"  # input untouched


def test_every_report_label_has_a_russian_entry():
    import re  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    from axiom.i18n import RU  # noqa: PLC0415

    template = (Path(__file__).parent.parent / "src/axiom/report/report.html.j2").read_text()
    keys = re.findall(r'_\("((?:[^"\\]|\\.)*)"', template)
    assert keys and [k for k in keys if k not in RU] == []
