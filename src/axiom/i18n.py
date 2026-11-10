# ruff: noqa: E501 - translation tables read better unwrapped
"""Display translation of backend texts (rule messages, expected/actual, report labels).

Stored findings stay English: translation happens only when a response or report is rendered with
`lang=ru`. Tokens (status, severity, event, rule ids, IFC classes) are never translated here.
Text without a matching entry passes through unchanged (e.g. IDS facet results, which come from the IDS file).
"""

from __future__ import annotations

import re
from typing import Literal

Lang = Literal["en", "ru"]
LANGS: tuple[str, ...] = ("en", "ru")

_C = r"(Ifc\w+)"
# (pattern, Russian template using \1, \2 ...); patterns are matched against the whole text
_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(p), r)
    for p, r in (
        (rf"{_C} has no material assigned", r"\1: не назначен материал"),
        (rf"{_C} has no Name", r"\1: не заполнено имя (Name)"),
        (rf"{_C} has no classification reference", r"\1: нет ссылки на классификатор"),
        (rf"{_C} has no base quantity set", r"\1: нет базового набора количеств"),
        (rf"{_C} has no geometric representation", r"\1: нет геометрического представления"),
        (rf"{_C} is not located in any building storey", r"\1: не размещён ни на одном этаже"),
        (
            rf"{_C} is not located in any facility or spatial element",
            r"\1: не размещён ни в одном пространственном элементе",
        ),
        (r"GlobalId (\S+) is shared by (\d+) elements", r"GlobalId \1 используется \2 элементами"),
        (
            r"declared volume disagrees with geometry; likely unit-scale error \((x[\d.e+]+)\)",
            r"заявленный объём расходится с геометрией; вероятна ошибка масштаба единиц (\1)",
        ),
        (r"(\d+) elements", r"элементов: \1"),
        (r"container (?!none$)(\S+)", r"контейнер \1"),
        (
            r"(\S+)\.(\S+) within (x[\d.e+]+) of geometry volume",
            r"\1.\2 в пределах \3 от объёма по геометрии",
        ),
        (r"(\S+) (\S+) m3 vs geometry (\S+) m3 \((x\S+)\)", r"\1 \2 м³, по геометрии \3 м³ (\4)"),
        (r"(\d+) subtype entities skipped", r"пропущено подтипов: \1"),
        (r"(\w+) present", r"\1 присутствует"),
        (
            r"at least (\d+) entity matching the applicability",
            r"не менее \1 объекта, подходящего под применимость",
        ),
        (r"all (\S+) subtypes checked", r"проверены все подтипы \1"),
    )
)

RU: dict[str, str] = {
    # rule texts
    "none": "нет",
    "container none": "контейнер отсутствует",
    "body representation": "представление Body",
    "unique GlobalId": "уникальный GlobalId",
    "contained in a storey": "размещён на этаже",
    "contained in a spatial element": "размещён в пространственном элементе",
    "material association": "назначенный материал",
    "non-empty Name": "непустое имя (Name)",
    "classification reference": "ссылка на классификатор",
    "Qto_*BaseQuantities": "Qto_*BaseQuantities",
    "declared volume disagrees with geometry": "заявленный объём расходится с геометрией",
    "model has no IfcBuildingStorey or IfcFacility; containment cannot be assessed":
        "в модели нет IfcBuildingStorey или IfcFacility; размещение проверить нельзя",
    "no entities matching the applicability": "нет объектов, подходящих под применимость",
    "0 matching entities": "подходящих объектов: 0",
    # report labels
    "Axiom audit report": "Отчёт Axiom о проверке",
    "Model audit report": "Отчёт о проверке модели",
    "Unnamed project": "Проект без названия",
    "revision": "ревизия",
    "audited": "проверено",
    "Model Health Index": "Индекс качества модели (MHI)",
    "Score withheld: blocking findings ({ids}) must be fixed first.":
        "Балл не рассчитан: сначала нужно устранить блокирующие замечания ({ids}).",
    "checks evaluated": "проверок выполнено",
    "findings": "замечаний",
    "Dimension": "Критерий",
    "Score": "Балл",
    "Weight": "Вес",
    "Passed": "Выполнено",
    "Failed": "Нарушено",
    "Not evaluated": "Не проверено",
    "The MHI measures information completeness and consistency of the model file. It is not a structural or "
    "safety assessment.": "MHI оценивает полноту и согласованность информации в файле модели. Это не оценка "
    "конструкций и не оценка безопасности.",
    "Findings": "Замечания",
    "No findings: every evaluated check passed or did not apply.":
        "Замечаний нет: все выполненные проверки пройдены или неприменимы.",
    "Severity": "Критичность",
    "Status": "Статус",
    "Rule": "Правило",
    "Element": "Элемент",
    "Expected": "Ожидалось",
    "Actual": "Фактически",
    "model": "модель",
    "Changes since revision {n}": "Изменения с ревизии {n}",
    "GlobalIds look regenerated for {classes}. Element continuity cannot be trusted, so all finding events are "
    "marked uncertain.": "Похоже, GlobalId пересозданы для {classes}. Соответствие элементов ненадёжно, поэтому "
    "все изменения замечаний помечены как неоднозначные.",
    "The two audits used different IDS files; affected events are uncertain.":
        "В двух проверках использованы разные файлы IDS; затронутые изменения неоднозначны.",
    "The two audits used different rule sets; affected events are uncertain.":
        "В двух проверках использованы разные наборы правил; затронутые изменения неоднозначны.",
    "Elements": "Элементы",
    "no element changes": "элементы не изменялись",
    "Event": "Событие",
    "Note": "Примечание",
    "No new, resolved or recurring findings.": "Нет новых, устранённых или повторных замечаний.",
    "Property changes": "Изменения свойств",
    "Change": "Изменение",
    "Path": "Путь",
    "Old": "Было",
    "New": "Стало",
    "Reproducibility": "Воспроизводимость",
    "Generated by Axiom BIM ({fmt}). Re-running the same file with the same rule set, IDS and scoring config gives "
    "the same findings.": "Сформировано Axiom BIM ({fmt}). Повторная проверка того же файла с теми же правилами, IDS "
    "и настройками оценки даёт те же замечания.",
    # tokens shown in reports (display only)
    "critical": "критично", "high": "высокая", "medium": "средняя", "low": "низкая", "info": "инфо",
    "pass": "выполнено", "fail": "нарушение", "warning": "предупреждение", "error": "ошибка",
    "not evaluated": "не проверено", "not applicable": "неприменимо",
    "new": "новое", "resolved": "устранено", "persistent": "сохраняется", "recurring": "повторное",
    "changed": "изменено", "uncertain": "неоднозначно", "added": "добавлено", "removed": "удалено",
    "modified": "изменено", "element removed": "элемент удалён", "rule version changed": "изменилась версия правила",
    "property completeness": "полнота свойств", "ids compliance": "соответствие IDS",
    "geometry integrity": "целостность геометрии", "spatial integrity": "пространственная структура",
    "material completeness": "полнота материалов", "classification quality": "качество классификации",
    "model consistency": "согласованность модели",
}  # fmt: skip


def tr(lang: str, text: str | None, **vars: object) -> str | None:
    """Translate `text` for display; `{name}` placeholders are filled from `vars` in either language."""
    if text is None:
        return None
    out = _ru(text) if lang == "ru" else text
    return out.format(**vars) if vars else out


def _ru(text: str) -> str:
    if text in RU:
        return RU[text]
    for pattern, template in _PATTERNS:
        m = pattern.fullmatch(text)
        if m:
            return m.expand(template)
    return text


def token(lang: str, value: str | None) -> str | None:
    """A machine token for display: `not_evaluated` -> "не проверено"."""
    return None if value is None else tr(lang, value.replace("_", " "))


def localize_finding(finding: dict, lang: str) -> dict:
    if lang != "ru":
        return finding
    return {**finding, **{k: tr(lang, finding.get(k)) for k in ("message", "expected", "actual")}}
