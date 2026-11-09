---
id: P03
skills: [mattpocock-skills:tdd, mattpocock-skills:codebase-design]
---
# P03 — Rule engine + Finding + `axiom audit`

Context: `docs/PLAN.md` §3 "Finding identity" + "Finding status vocabulary"; D-04, D-10. Proposal Module B §2 (grep `### 2. Custom rule engine`).

1. `axiom/findings.py`: `Finding` pydantic model (fields per PLAN §3) + `identity_key()` per PLAN formula. Status/severity/category as enums.
2. `axiom/rules/`: `@rule(id, version, name, category, severity, dimension, applies_to=[ifc classes], description)` decorator registering a function `(element, snapshot) -> CheckResult(status, issue_key, expected, actual, evidence)`. Rule set version = hash of (rule ids + versions + params yaml). Engine runs every applicable rule on every applicable element; an exception inside a rule → `error` result, never crashes the audit; elements a rule can't assess → `not_evaluated`.
3. Initial rules (each with a docstring citing the IFC concept it relies on, and a test using a fixture):
   - GEO-001 element has body representation (IfcWall/Column/Beam/Slab/Member/Footing)
   - GEO-002 duplicate GlobalId (model-level)
   - SPA-001 physical element contained in a storey (direct or via aggregate)
   - SPA-002 storey elevations strictly increasing / no duplicate names
   - MAT-001 structural element has a material association (Column/Beam/Slab/Footing/Member)
   - MET-001 element has a non-empty Name
   - CLS-001 element has at least one classification reference (warning severity; many models lack it legitimately)
   - QTO-001 element has a base Qto set with ≥1 quantity
4. `axiom/services/audits.py`: `run_audit(revision_id, ids_path=None)` → AuditRun + findings persisted (tables + migration). Store only non-pass findings as rows; store pass/NA/not_evaluated **counts** per rule in `summary_json` (needed by MHI coverage).
5. CLI `axiom audit file.ifc [--json out.json]` (ingest if needed → audit → print table). JSON includes reproducibility block (D-10).
6. Determinism test: audit same fixture twice → identical findings (ignoring ids/timestamps).

**DONE WHEN:** every fixture's expected.yaml findings are produced exactly (no extras on `clean`); determinism test green.
