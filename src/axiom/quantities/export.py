"""Quantity table as CSV for estimators. Formatting only: numbers come from `aggregate`/`quantity_delta`."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable

from axiom.quantities.aggregate import QuantityDelta, QuantityRow

COLUMNS = ("group", "qto", "quantity", "method", "unit", "total", "elements", "missing", "previous", "change")
BOM = "﻿"  # Excel assumes a legacy code page without it; storey and material names are often Cyrillic
PRECISION = 6


def _key(r: QuantityRow | QuantityDelta) -> tuple[str, str, str, str]:
    return (r.group, r.qto, r.quantity, r.method)


def _change(d: QuantityDelta | None) -> dict:
    if d is None:
        return {}
    change = None if d.old is None or d.new is None else round(d.new - d.old, PRECISION)
    return {"previous": d.old, "change": change}


def to_csv(rows: Iterable[QuantityRow], deltas: Iterable[QuantityDelta]) -> str:
    """One line per (group, quantity, method). A group only the previous revision had keeps a line."""
    delta = {_key(d): d for d in deltas}
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(
            {
                **dict(zip(COLUMNS[:5], (*_key(r), r.unit), strict=True)),
                "total": r.total,
                "elements": r.count,
                "missing": len(r.missing),
                **_change(delta.pop(_key(r), None)),
            }
        )
    for d in delta.values():  # present before, gone now
        w.writerow({**dict(zip(COLUMNS[:5], (*_key(d), d.unit), strict=True)), **_change(d)})
    return BOM + out.getvalue()
