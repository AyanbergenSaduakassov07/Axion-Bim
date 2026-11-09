---
id: P05
skills: [mattpocock-skills:tdd]
---
# P05 — Model Health Index

Context: `docs/PLAN.md` §3 "MHI (v1)" (formula, coverage, critical gate). Proposal Module C.

1. `axiom/score/config/default.yaml`: version, dimensions {property_completeness, ids_compliance, geometry_integrity, spatial_integrity, material_completeness, classification_quality, model_consistency} with weights summing to 1 and rule-id→dimension mapping (rules already declare `dimension`; IDS findings map to `ids_compliance`). Validate weights sum to 1 ± 1e-9 on load.
2. `axiom/score/mhi.py`: pure function `(audit summary counts, config) -> MhiResult` with per-dimension {score|null, passed, failed, not_evaluated, errors, weight, effective_weight, contribution}, overall score, coverage %, `blocked: bool` + blocking finding ids. Null dimensions redistribute weight proportionally and are listed in `notes`.
3. Persist scoring config JSON in AuditRun; `services/audits.py` computes MHI after audit.
4. CLI: `axiom audit` prints MHI table (dimension, score, contribution, coverage) and the critical gate.
5. Numeric tests: hand-computed cases (all pass = 100; one dimension empty → redistribution exact; critical fail → blocked even at 98); property test that score ∈ [0,100].

**DONE WHEN:** tests green; MHI on `clean` = 100 with full coverage (except classification if not modeled — then that must show as warning, not fail; document).
