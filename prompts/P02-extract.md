---
id: P02
skills: [mattpocock-skills:tdd, mattpocock-skills:domain-modeling]
---
# P02 — Extraction → Snapshot → SQLite

Context: `docs/PLAN.md` §3 "Core entities"; D-05. Proposal Module A (grep `## Module A` in `docs/PROPOSAL.md`).

1. `axiom/extract/`: `extract(path) -> Snapshot` (pydantic). Snapshot = revision metadata (schema, units, authoring app, project name, georef if present, file sha256, size) + elements (GlobalId, class, name, description, object_type, predefined_type, storey GlobalId, aggregate parent, has_representation, representation types) + property values (pset, name, value, unit) + quantities from Qto sets (raw unit + SI-normalized) + material associations (layered/profile/constituent flattened to names, keep kind) + classification refs + spatial tree. Use `ifcopenshell.util.element` / `util.unit` — do not hand-walk relations the util already handles.
2. Units: normalize to SI using the file's unit assignment; keep raw. Test with `weird_units`.
3. Profiling: `profile(snapshot)` → counts by class, missing name/psets/material/geometry/containment, completeness per class.
4. `axiom/repo/` SQLAlchemy Core tables per PLAN §3 for Project/Model/Revision/Element/PropertyValue/Quantity/MaterialAssoc/Classification; Alembic initial migration; SQLite at `data/axiom.db` (env `AXIOM_DB_URL`). `axiom/services/revisions.py`: `ingest(model_id, path)` = hash → store file content-addressed under `data/files/` → extract → persist. Idempotent on same hash.
5. CLI `axiom inspect file.ifc [--json]` prints metadata + profile.
6. Tests: each fixture's expected.yaml counts; GlobalId round-trip; unit normalization numeric test (mm→m); re-ingest same file creates no duplicate.

Geometry bboxes are NOT in this prompt (optional later; keep `has_representation` only).

**DONE WHEN:** tests green; `axiom inspect` on the P00 public sample completes and prints sane counts; timing noted in `docs/spikes/00-findings.md` appendix.
