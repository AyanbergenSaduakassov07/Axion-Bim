---
id: P00
skills: [mattpocock-skills:prototype]
---
# P00 — De-risk spike (throwaway)

**Goal:** prove the three things that could kill the plan, before any architecture is committed.

Context: `docs/PLAN.md` §2 item 5, §6; `docs/DECISIONS.md` D-02, D-04, D-08.

Work in `spikes/` (gitignored except `docs/spikes/00-findings.md`).

1. **Python:** `uv init` a scratch env on Python 3.12, add `ifcopenshell==0.9.0.post1 ifctester==0.9.0 ifcdiff==0.9.0`. Download one public IFC4 sample (buildingSMART sample-test-files repo; record URL + license). Print: schema, units, element counts by class, 5 elements with GlobalId + psets + material. Time it.
2. **IDS:** take one IDS from `github.com/buildingSMART/IDS` test cases, run `ifctester` against the sample, dump the result structure (what object gives per-entity pass/fail, expected vs actual). Record the exact API path we will adapt in P04.
3. **IfcDiff:** run it on the sample vs a copy with one property edited via `ifcopenshell.api`. Record runtime and output shape (to confirm D-03 or overturn it).
4. **Viewer:** Vite + TS page with `@thatopen/components` / `components-front` / `fragments` 3.6.x + `web-ifc` 0.0.78 (check context7 for current v3 API first). Must: load the sample IFC, click an element → show its GlobalId, and given a GlobalId string → highlight + zoom to it. Note the GlobalId ↔ local id mapping API.
5. Write `docs/spikes/00-findings.md`: versions that worked, API snippets for each of 1–4, timings, gotchas, and a go/no-go per item. If the viewer fails after 2 honest attempts, evaluate the fallback in D-08 and write a superseding decision.

**DONE WHEN:** findings doc exists with go/no-go for all four; any overturned decision is appended to `docs/DECISIONS.md`.
