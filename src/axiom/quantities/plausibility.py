"""QTO-002: declared Qto volume vs tessellated geometry volume (D-12). Opt-in: needs a geometry pass."""

from __future__ import annotations

import math
from collections.abc import Mapping

from axiom.extract.snapshot import Element, Snapshot
from axiom.findings import CheckStatus
from axiom.rules.builtin import GEOMETRIC
from axiom.rules.engine import AuditOutput, CheckResult, ModelContext, Rule, RuleMeta, Scope, run_rules

RATIO_LIMIT = 2.0  # Gross vs net (openings) stays well inside x2; unit-scale errors are x1000+
MIN_GEOMETRY_M3 = 1e-9  # open shells tessellate to ~0 volume: not measurable
UNIT_SCALES = (1e3, 1e6, 1e9)  # mm->m on a length, area, volume
VOLUME_NAMES = ("NetVolume", "GrossVolume")  # geometry has openings cut: compare net first

META = RuleMeta(
    id="QTO-002",
    version="2",
    name="Declared volume matches geometry",
    category="quantity",
    severity="medium",
    dimension="quantity",
    scope=Scope.ELEMENT,
    applies_to=GEOMETRIC,
    description=f"Qto NetVolume (or GrossVolume) within x{RATIO_LIMIT:g} of the geometry volume.",
)


def run_qto_002(snap: Snapshot, volumes: Mapping[int, float], model_id: int) -> AuditOutput:
    """volumes: step_id -> m3 from geometry_volumes()."""

    def check(el: Element, _ctx: ModelContext) -> CheckResult:
        return _check(el, volumes.get(el.step_id))

    out = run_rules(snap, model_id, [Rule(META, check)])
    return AuditOutput(out.findings, out.counts, META.version, out.rules)


def _check(el: Element, geo: float | None) -> CheckResult:
    q = next((q for n in VOLUME_NAMES for q in el.quantities if q.name == n), None)
    if q is None:
        return CheckResult(CheckStatus.NOT_APPLICABLE)
    if geo is None or geo < MIN_GEOMETRY_M3:
        return CheckResult(CheckStatus.NOT_EVALUATED, "volume:no_geometry")
    ratio = q.si_value / geo
    if 1 / RATIO_LIMIT <= ratio <= RATIO_LIMIT:
        return CheckResult(CheckStatus.PASS)
    hint = next((s for s in UNIT_SCALES if math.isclose(max(ratio, 1 / ratio), s, rel_tol=0.05)), None)
    return CheckResult(
        CheckStatus.FAIL,
        "volume:implausible",
        expected=f"{q.qto}.{q.name} within x{RATIO_LIMIT:g} of geometry volume",
        actual=f"{q.name} {q.si_value:.6g} m3 vs geometry {geo:.6g} m3 (x{ratio:.4g})",
        message="declared volume disagrees with geometry"
        + (f"; likely unit-scale error (x{hint:g})" if hint else ""),
        evidence={
            "qto": q.qto,
            "quantity": q.name,
            "qto_m3": q.si_value,
            "geometry_m3": geo,
            "ratio": ratio,
            "unit_scale_hint": hint,
        },  # fmt: skip
    )
