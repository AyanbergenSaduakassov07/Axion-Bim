"""Quantities as CSV for the estimator (audit gap G6): the JSON numbers, with unit, method and delta."""

import csv
import io

from tests.test_api import V1, _model, _upload, client  # noqa: F401 - client is a fixture

COLUMNS = ["group", "qto", "quantity", "method", "unit", "total", "elements", "missing", "previous", "change"]


def test_quantities_csv_matches_json_and_carries_the_delta(client, ifc_path):  # noqa: F811
    c = client
    mid = _model(c)
    r1 = _upload(c, mid, ifc_path("rev1"))["result"]["revision_id"]
    r2 = _upload(c, mid, ifc_path("rev2"))["result"]["revision_id"]
    url, params = f"{V1}/revisions/{r2}/quantities", {"by": "class", "against": r1}
    data = c.get(url, params=params).json()

    res = c.get(url, params=params | {"format": "csv"})
    assert res.status_code == 200 and res.headers["content-type"].startswith("text/csv")
    assert res.text.startswith("﻿")  # Excel reads UTF-8 only with a BOM
    rows = list(csv.DictReader(io.StringIO(res.text.lstrip("﻿"))))
    assert list(rows[0]) == COLUMNS
    assert all(r["method"] in ("qto", "geometry") for r in rows)

    key = lambda r: (r["group"], r["qto"], r["quantity"], r["method"])  # noqa: E731
    by_key = {key(r): r for r in rows}
    for j in data["rows"]:
        assert float(by_key[key(j)]["total"]) == j["total"] and by_key[key(j)]["unit"] == (j["unit"] or "")
    changed = [d for d in data["delta"] if d["old"] is not None and d["new"] is not None]
    assert changed, "fixture rev1 -> rev2 is expected to change a quantity"
    d = changed[0]
    assert float(by_key[key(d)]["change"]) == round(d["new"] - d["old"], 6)
    assert len(rows) == len({key(x) for x in data["rows"] + data["delta"]})  # removed groups stay listed
