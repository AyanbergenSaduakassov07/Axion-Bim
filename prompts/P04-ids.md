---
id: P04
skills: [mattpocock-skills:tdd]
---
# P04 — IDS validation via IfcTester

Context: D-04; `docs/spikes/00-findings.md` item 2 (the IfcTester API path). Check context7 / ifctester source for 0.9.0 before coding.

1. `axiom/ids/adapter.py`: `run_ids(ifc_path, ids_path) -> list[CheckResult-like]` mapping IfcTester results into `Finding`: rule_id = `IDS:<spec name or identifier>`, rule_version = IDS file sha256[:12], issue_key = `<spec_idx>/<requirement facet type>/<facet descriptor>`, expected/actual from the failure reason. Applicability-only specs with zero applicable entities → `not_applicable`, not pass. Any spec the checker didn't evaluate → `not_evaluated`. Never reinterpret a requirement.
2. Store IDS files content-addressed; `AuditRun.ids_hash`. Severity default `high` for required, `medium` for optional (document in DECISIONS if you choose differently).
3. `axiom audit --ids req.ids` merges IDS findings with rule findings.
4. Write `examples/ids/structural-basic.ids` (columns/beams need material + Pset_*Common.LoadBearing; walls need Pset_WallCommon.FireRating) — validate it against the official IDS XSD (ifctester can). Use it in tests on `missing_material` and `missing_props`.
5. Conformance: run a handful of buildingSMART IDS test cases (pass/fail pairs) through the adapter; results must match the suite's expected outcome.

**DONE WHEN:** fixture tests + conformance subset green; spec failures show expected vs actual in CLI output.
