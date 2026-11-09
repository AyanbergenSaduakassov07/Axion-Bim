"""Model Health Index v1 (PLAN §3, D-15). Pure: audit counts + findings + config -> MhiResult.

s_i = passed / (passed + failed). warning / not_evaluated / error count toward coverage only;
not_applicable is neither scored nor a coverage gap. Null dimensions give their weight to the rest.
Any critical fail sets `blocked`, whatever the score.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fnmatch import fnmatchcase
from importlib.resources import files
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from axiom.findings import Finding

STATUSES = ("pass", "fail", "warning", "not_evaluated", "error")


class ScoringConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    weights: dict[str, float]
    rules: dict[str, str]  # fnmatch pattern -> dimension, first match wins

    @model_validator(mode="after")
    def _check(self) -> ScoringConfig:
        if not math.isclose(sum(self.weights.values()), 1.0, abs_tol=1e-9):
            raise ValueError(f"weights must sum to 1, got {sum(self.weights.values())}")
        if unknown := set(self.rules.values()) - set(self.weights):
            raise ValueError(f"rules map to unknown dimension(s): {sorted(unknown)}")
        return self

    def dimension_of(self, rule_id: str) -> str | None:
        return next((d for pat, d in self.rules.items() if fnmatchcase(rule_id, pat)), None)


def load_config(path: Path | None = None) -> ScoringConfig:
    src = Path(path) if path else files("axiom.score") / "config" / "default.yaml"
    return ScoringConfig(**yaml.safe_load(src.read_text()))


@dataclass(frozen=True)
class DimensionScore:
    score: float | None  # 0..100, None = nothing evaluated
    passed: int
    failed: int
    warnings: int
    not_evaluated: int
    errors: int
    weight: float
    effective_weight: float
    contribution: float

    @property
    def coverage(self) -> float | None:
        evaluated = self.passed + self.failed + self.warnings
        total = evaluated + self.not_evaluated + self.errors
        return 100 * evaluated / total if total else None


@dataclass(frozen=True)
class MhiResult:
    score: float | None
    coverage: float | None
    blocked: bool
    blocking: tuple[str, ...]  # identity keys of critical fails
    dimensions: dict[str, DimensionScore]
    notes: tuple[str, ...]
    config_version: str


def compute_mhi(
    counts: dict[str, dict[str, int]], findings: tuple[Finding, ...], cfg: ScoringConfig
) -> MhiResult:
    tallies = {d: dict.fromkeys(STATUSES, 0) for d in cfg.weights}
    notes = []
    for rule_id, c in sorted(counts.items()):
        dim = cfg.dimension_of(rule_id)
        if dim is None:
            notes.append(f"rule {rule_id} is not mapped to a dimension; not scored")
            continue
        for s in STATUSES:
            tallies[dim][s] += c.get(s, 0)
    raw = {
        d: (t["pass"] / (t["pass"] + t["fail"]) if t["pass"] + t["fail"] else None)
        for d, t in tallies.items()
    }
    live = sum(cfg.weights[d] for d, s in raw.items() if s is not None)
    dims = {d: _dimension(tallies[d], raw[d], cfg.weights[d], live) for d in cfg.weights}
    notes += [f"{d}: nothing evaluated, weight redistributed" for d, s in raw.items() if s is None]
    blocking = tuple(f.identity_key for f in findings if f.severity == "critical" and f.status == "fail")
    evaluated = sum(t["pass"] + t["fail"] + t["warning"] for t in tallies.values())
    total = evaluated + sum(t["not_evaluated"] + t["error"] for t in tallies.values())
    return MhiResult(
        score=round(math.fsum(x.contribution for x in dims.values()), 6) if live else None,
        coverage=100 * evaluated / total if total else None,
        blocked=bool(blocking),
        blocking=blocking,
        dimensions=dims,
        notes=tuple(notes),
        config_version=cfg.version,
    )


def _dimension(t: dict[str, int], s: float | None, weight: float, live: float) -> DimensionScore:
    eff = weight / live if s is not None else 0.0
    return DimensionScore(
        score=None if s is None else 100 * s,
        passed=t["pass"],
        failed=t["fail"],
        warnings=t["warning"],
        not_evaluated=t["not_evaluated"],
        errors=t["error"],
        weight=weight,
        effective_weight=eff,
        contribution=100 * s * eff if s is not None else 0.0,
    )
