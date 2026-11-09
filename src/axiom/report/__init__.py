"""Audit reports: one canonical JSON dict, rendered to JSON, CSV (findings) or self-contained HTML."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

FORMAT_VERSION = "axiom-report/1"
FORMATS = {"json": "application/json", "csv": "text/csv", "html": "text/html"}
CSV_FIELDS = (
    "global_id", "element_name", "ifc_class", "rule_id", "rule_version", "status", "severity",
    "category", "dimension", "expected", "actual", "message", "identity_key",
)  # fmt: skip

_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent),
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render(report: dict, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(report, indent=2, default=str)
    if fmt == "csv":
        return _csv(report["findings"])
    if fmt == "html":
        return _env.get_template("report.html.j2").render(r=report)
    raise ValueError(f"unknown report format {fmt!r}; use one of {', '.join(FORMATS)}")


def _csv(findings: list[dict]) -> str:
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=CSV_FIELDS, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    w.writerows(findings)
    return out.getvalue()
