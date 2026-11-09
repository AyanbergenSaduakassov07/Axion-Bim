---
id: P06
skills: [mattpocock-skills:tdd]
---
# P06 — Revision engine + issue regression (the differentiator)

Context: `docs/PLAN.md` §2 item 1, §3 "Finding identity"; D-03. Proposal Module D (grep `## Module D`).

1. `axiom/revision/diff.py`: pure `diff(old: Snapshot, new: Snapshot) -> list[Change]`. Match by GlobalId. Kinds: `added | removed | modified`. For modified, emit one Change per path: `attr:Name`, `pset:<Pset>.<Prop>`, `qto:<Qto>.<Q>`, `material`, `classification`, `container`, `representation`. Values compared after unit normalization; float tolerance as named constant.
2. Identity stability check: if removed and added counts per class are both > 50% of the class → comparison flagged `identity_unstable` and all finding events become `uncertain`. Duplicate GlobalIds → those elements `uncertain`.
3. `axiom/revision/regression.py`: pure `classify(history: list[set[identity_key] + evidence], current) -> FindingEvent[]`: new / resolved / persistent / recurring (present earlier, absent in previous, present now) / changed (same key, different actual/evidence) / uncertain. History = all prior audits of the same model, ordered.
4. Impact: for each Change, list rules whose applicability covers the element and which finding events touched that element → `impact` records ("material changed on column X → MAT-001 resolved").
5. Persist Comparison, Change, FindingEvent (migration). `services/comparisons.py: compare(model_id, old_rev, new_rev)`; ingestion of a new revision auto-compares with the previous one.
6. CLI `axiom compare r1.ifc r2.ifc [r3.ifc ...] [--ids x.ids] [--json]` → per step: change counts by class, property changes, finding events, MHI delta with per-dimension contribution delta.
7. Golden tests on rev1→rev2→rev3 matching their expected.yaml exactly (including one `recurring`).
8. Optional: `--ifcdiff` flag runs IfcDiff and reports disagreement count with our diff (cross-check only).

**DONE WHEN:** golden tests green; `axiom compare` output on rev1..rev3 is readable enough to screenshot for the README.
