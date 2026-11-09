# Axiom BIM — Lead-dev plan

Status: approved-for-execution draft, 2026-11-09. Source proposal: `docs/PROPOSAL.md` (verbatim).
Decisions with rationale: `docs/DECISIONS.md`.

## 1. Verdict

The product thesis is strong; the delivery plan is not. Keep the thesis, cut the plan.

- **Keep:** revision-aware QA as the headline, deterministic engine with AI as a thin layer, finding identity across revisions, transparent MHI, "never claim a check passed if it was not evaluated". These are the right instincts and they are what an engineer reviewer will respect.
- **Cut:** 8-package monorepo, Postgres + Redis + RQ + object storage on day one, YAML rule DSL, users/orgs/auth, BCF and PDF in v1, a 14-day promise for all eight modules.
- **Change:** build the engine as a **library + CLI first**. The CLI *is* the product core, is trivially testable, and is already demoable (`axiom compare rev1.ifc rev2.ifc` printing new/resolved/recurring findings is the whole differentiator in one command). API and UI wrap it afterwards.

Realistic pace: CLI core (P00–P07) ≈ 7–9 focused days. Full first release (P00–P13) ≈ 4 weeks. The 14-day table in the proposal assumes nothing goes wrong with the viewer, which is the riskiest piece.

## 2. Ten things I'd change, ranked by impact

1. **Diff our own snapshot, not IFC files.** We already extract every element, pset, material and relation into a normalized snapshot. Diffing two snapshots by GlobalId is set arithmetic: fast, deterministic, at exactly the granularity the finding engine needs. IfcDiff is slow on large models and its output would have to be re-mapped anyway. Use IfcDiff only as an optional cross-check / geometry-change signal. (D-03)
2. **IDS for information requirements, Python for everything else.** "Column must have material", "wall must have FireRating" — that is literally what IDS expresses, and IfcTester already evaluates it correctly. A home-grown YAML DSL would duplicate IDS badly and become an interpreter to maintain. Custom rules = geometry, spatial integrity, duplicates, consistency — written as small Python functions with declared metadata. Both emit one `Finding` schema. (D-04)
3. **SQLite + subprocess workers, no Redis/Postgres yet.** Single-user local tool first. SQLAlchemy Core + Alembic so Postgres is a URL change later. Background work runs in a child process — not for scale, for **safety**: IfcOpenShell is C++ and a malformed IFC can segfault; a child process with timeout + memory limit protects the API. (D-05, D-06)
4. **Generate test fixtures in code.** `ifcopenshell.api` can build IFC models programmatically. A fixture factory that creates "clean", "missing material", "no geometry", "rev2 with 3 known changes", "rev3 with a recurring defect" gives us exact ground truth. Public models (buildingSMART samples) are for benchmarks and realism, not correctness tests. (D-07)
5. **Kill the viewer risk on day 1.** ThatOpen is at v3.6 with Fragments; its API has churned across majors. A throwaway spike (load IFC, click → GlobalId, highlight-by-GlobalId) before any architecture commitment. If it fails, fallback is xeokit or plain web-ifc + three.js. (P00)
6. **One Python package, many modules.** `src/axiom/{extract,rules,ids,score,revision,quantities,api,jobs,report,copilot}`. Split into packages only when a second consumer appears. Same for the frontend: one Vite app.
7. **No auth/orgs in v1.** Local single-user. Keep `project_id` scoping in every query so tenancy can be added without schema surgery. The proposal's own §20 says this; §8/§11 contradict it.
8. **HTML report first, PDF = print the HTML.** One template, two outputs. BCF only after the core works, validated against BCF 3.0 with a real viewer (BIMcollab Zoom free / Solibri Anywhere).
9. **Copilot gets an eval set before a UI.** 20–30 questions over fixture models with expected GlobalIds / finding IDs. Post-check: every GlobalId in the answer must appear in a tool result in that turn, else the answer is rejected. That's the "evidence-first" claim made measurable.
10. **Portfolio coherence (read this).** You now have three IFC products: Structra (drawing → IFC), AXION (text → IFC, with "norm checks"), Axiom (IFC → QA). Two risks: (a) **"Axiom" vs "Axion" is one letter apart** — recruiters will confuse them; rename one. (b) AXION's norm checks overlap Axiom's validation. Best story: Axiom is the **QA engine the other two feed into** — "Structra/AXION produce IFC; Axiom audits it." That is a stronger portfolio than three silos.

## 3. Architecture (v1)

```
            ┌──────────── apps/web (Vite·React·TS·Tailwind·TanStack Query·ThatOpen 3.x) ───────────┐
            │  Overview · Quality Center · Model Explorer (3D) · Revisions · Quantities · Copilot   │
            └───────────────────────────────▲──────────────────────────────────────────────────────┘
                                            │ REST (OpenAPI → generated TS types)
┌───────────────────────── src/axiom (one Python package, uv) ────────────────────────────────────┐
│ api/  FastAPI routes ──► services/ (only layer that touches repos) ──► repo/ SQLAlchemy Core      │
│ jobs/ job table + subprocess runner (timeout, RSS limit) ──► pipeline: extract→audit→score→diff  │
│ extract/  ifcopenshell → Snapshot (elements, psets, qtos, materials, classif., containment, units)│
│ rules/    Python rules w/ metadata   ids/ IfcTester adapter      ── both ──► Finding (one schema) │
│ score/    MHI from findings + versioned config        revision/ snapshot diff + finding regression│
│ quantities/ Qto-sourced vs geometry-computed, tagged  report/ JSON · CSV · HTML                   │
│ copilot/  Claude tool-use over services (read-only), citation post-check                         │
│ cli.py    axiom inspect | audit | compare | report   (same services as the API)                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
   storage: data/axiom.db (SQLite)  ·  data/files/<sha256>.ifc (content-addressed, local adapter)
```

Data flow per revision: upload → sha256 → store file → job: `extract` (snapshot rows) → `audit` (rules + IDS → findings) → `score` (MHI) → if previous revision: `compare` (changes + finding events).

### Core entities (relational; JSON only for evidence/metadata)

`Project, Model, Revision(file_hash, schema, status, metadata_json), Element(revision_id, global_id, ifc_class, name, predefined_type, storey_global_id, has_geometry, …), PropertyValue(element_id, pset, name, value, unit, source), MaterialAssoc, Classification, Quantity(element_id, name, value, unit, normalized_value, method: qto|geometry), RuleSet(version, hash), IdsSpec(hash), AuditRun(revision_id, ruleset_hash, ids_hash, engine_version, scoring_config_json, status), Finding(audit_run_id, identity_key, rule_id, rule_version, global_id, status, severity, category, expected, actual, evidence_json), Comparison(old_rev, new_rev, summary_json), Change(comparison_id, global_id, kind, path, old, new), FindingEvent(comparison_id, identity_key, event: new|resolved|persistent|recurring|changed|uncertain), Job`.

### Finding identity

`identity_key = sha1(model_id | rule_id | global_id | issue_key)` where `issue_key` is the normalized condition (e.g. `material:missing`, `pset:Pset_WallCommon.FireRating:missing`, IDS: `spec_id/requirement_idx/facet`). Recurring = key present in audit N, absent in N-1, present earlier. Uncertain = GlobalId missing/duplicated, or element matched only heuristically (heuristic matching is out of v1 scope; v1 marks these uncertain and moves on).

### Finding status vocabulary (exact)

Check result: `pass | fail | warning | not_applicable | not_evaluated | error`. Revision event: `new | resolved | persistent | recurring | changed | uncertain`. Severity: `critical | high | medium | low | info`. Never merge these vocabularies.

### MHI (v1)

Dimension score `s_i = passed / (passed + failed)` over checks mapped to dimension `i`; `not_evaluated`/`error`/`not_applicable` excluded and **reported** as coverage. Dimensions with zero evaluated checks get `null`, weight redistributed, and flagged. `MHI = Σ w_i s_i`. **Critical gate:** any `critical` fail caps displayed status at "Blocked" regardless of score. Config (weights, dimension→rule mapping) is versioned and stored in each AuditRun.

## 4. Milestones

| M | Prompts | Outcome you can show |
|---|---|---|
| M0 de-risk | P00 | Viewer + ifcopenshell + ifctester proven on this machine |
| M1 engine | P01–P05 | `axiom audit model.ifc --ids req.ids` → findings JSON + MHI, reproducible |
| M2 differentiator | P06–P07 | `axiom compare r1 r2` → changes + new/resolved/recurring findings + MHI delta |
| M3 app | P08–P11 | Upload in browser, Quality Center, click finding → element highlighted in 3D, revision view, HTML report |
| M4 AI | P12 | Copilot answers with cited GlobalIds; eval set passes ≥ 90% |
| M5 ship | P13 | Security pass, benchmarks on public models, README, 3-min demo |

Rule: if the viewer stalls, ship M2 + M3 without 3D rather than slip correctness. (Proposal §18 says the same — correct.)

## 5. Explicitly out of v1

Everything in proposal §20, plus: auth/orgs, Postgres, Redis, S3, BCF, PDF library, YAML rule DSL, heuristic element matching, clash detection, Kazakhstan requirement packs (good v2 candidate — natural tie-in with AXION).

## 6. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| ThatOpen 3.x API churn / docs lag | High | P00 spike, pin exact versions, wrap in one `viewer/` module |
| ifcopenshell segfault/hang on bad IFC | Medium | subprocess + timeout + RSS limit; job marked `error` with message |
| Geometry pass too slow on big models | Medium | geometry optional, multiprocess iterator, bbox only; benchmark |
| GlobalIds regenerated by authoring tool between revisions | Medium | detect (removed≈added same class/count) → flag whole comparison "identity unstable" |
| LLM cites non-existent elements | Medium | citation post-check, reject + retry once, eval set |
| LGPL obligations (IfcOpenShell) | Low | used as unmodified dependency; NOTICE file; app license MIT |

## 7. Open questions for Ayan (defaults applied if unanswered)

1. Rename to avoid Axiom/Axion clash? Default: keep "Axiom BIM" working name, decide before public repo.
2. Copilot provider: default Claude (`claude-sonnet-5-5` for answers). Gemini possible behind the same tool layer.
3. License: default MIT (compatible with LGPL dependency use).
4. Public demo deployment (needs auth + hosting) or local-only video demo? Default: local + video for v1.
