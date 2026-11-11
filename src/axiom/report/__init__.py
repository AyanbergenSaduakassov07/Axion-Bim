"""Audit reports: one canonical JSON dict, rendered to JSON, CSV (findings), HTML or BCF 3.0 / 2.1."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from axiom.i18n import localize_finding, token, tr

FORMAT_VERSION = "axiom-report/1"
FORMATS = {
    "json": "application/json",
    "csv": "text/csv",
    "html": "text/html",
    "bcf": "application/zip",
    "bcf21": "application/zip",  # BCF 2.1: Revit add-ins, Autodesk Construction Cloud
}
SUFFIX = {"bcf21": ".bcf"}  # file extension when it differs from the format name
CSV_FIELDS = (
    "global_id", "element_name", "ifc_class", "rule_id", "rule_version", "status", "severity",
    "category", "dimension", "expected", "actual", "message", "identity_key",
    "state", "assignee", "due_date", "note",
)  # fmt: skip

_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent),
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render(report: dict, fmt: str, lang: str = "en") -> str | bytes:
    """`lang` translates labels and rule texts for display; JSON stays canonical (English)."""
    if fmt == "json":
        return json.dumps(report, indent=2, default=str)
    if lang != "en":
        report = {**report, "findings": [localize_finding(f, lang) for f in report["findings"]]}
    if fmt == "csv":
        return _csv(report["findings"])
    if fmt == "html":
        return _env.get_template("report.html.j2").render(
            r=report, lang=lang, _=lambda text, **v: tr(lang, text, **v), tok=lambda v: token(lang, v)
        )
    if fmt in ("bcf", "bcf21"):
        from axiom.report.bcf import to_bcf  # noqa: PLC0415 - loads bcf-client/xsdata only when asked

        return to_bcf(report, "2.1" if fmt == "bcf21" else "3.0")
    raise ValueError(f"unknown report format {fmt!r}; use one of {', '.join(FORMATS)}")


def _csv(findings: list[dict]) -> str:
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=CSV_FIELDS, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    # triage columns: a finding nobody touched is open and unassigned
    w.writerows({"state": "open", **f, **(f.get("issue") or {})} for f in findings)
    return out.getvalue()
