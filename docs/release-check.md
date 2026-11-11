# Release check (P13) — 2026-11-09, commit after 4c94f57

Each step is run or marked "not run". Nothing here was assumed.

| # | Step | How checked | Result |
|---|---|---|---|
| 1 | Backend lint + tests | `uv run ruff check`, `uv run pytest -q` | pass: 179 passed, 1 xfailed (IfcTester 0.9.0 upstream bug, D-14) |
| 2 | Web typecheck, build, unit tests | `npm run typecheck && npm run build && npm test` | pass: 3 unit tests |
| 3 | Upload rev1 + IDS → job → Quality Center golden findings (4), MHI 95.2 | `e2e/smoke.spec.ts` | pass |
| 4 | Finding row → 3D viewer focuses the same GlobalId | `e2e/smoke.spec.ts` (dev hook) | pass |
| 5 | Model Explorer tree pick → focus | `e2e/smoke.spec.ts` | pass |
| 6 | Upload rev2, rev3 → auto-compare → recurring MAT-001 on C2, focus in head model | `e2e/revisions.spec.ts` | pass |
| 7 | MHI waterfall and comparison view render | `e2e/revisions.spec.ts` + `waterfall-steps.test.ts` | pass |
| 8 | Reports JSON/CSV/HTML from stored results | `tests/test_report.py` golden | pass |
| 9 | Copilot hidden without a key; app intact | `e2e/copilot.spec.ts`, `tests/copilot/test_api_copilot.py` | pass |
| 10 | Copilot citation chips deep-link to Explorer / Quality | `e2e/copilot.spec.ts` (stubbed API) | pass |
| 11 | Copilot live eval, free model `nvidia/nemotron-3-ultra-550b-a55b:free` | `python -m axiom.copilot.eval --only …` | partial: 6/25 cases run, 4/6 pass, 0 fabricated (free-tier daily cap). Target ≥90% **not demonstrated** |
| 12 | `docker compose build` + `up`: web 200, API via nginx 200, `/copilot` status | manual, this commit | pass. Upload rev1 + IDS and rev2 through nginx → job `done`, audit stored, file download 200; API runs as uid 10001 |
| 13 | Backend benchmarks on 4 public models | `benchmarks/run.py` → `benchmarks/RESULTS.md` | pass; models are small (≤1.7 MB, ≤68 elements), so this does not show behaviour on large models |
| 14 | Second real-world model end to end in the UI | upload + audit + explorer via Playwright on :3000, buildingSMART CC-BY samples (not committed) | pass (2026-11-10): Clinic_Architectural IFC2X3, MHI 89.3, 4252 open findings; Chesapeake Bay Bridge-Tunnel IFC4X3 17,553 elements, pipeline 19.5 s, viewer 15 s cold / 2.4 s cached, 3.97 MB fragments, ~160 MB heap. Found and fixed D-28 |
| 15 | CI on GitHub (`.github/workflows/ci.yml`) | `gh run` 42677896664 on cf4c621 | pass: python + web jobs green |
| 16 | Security review (upload, job runner, file serving, IDS parsing, copilot, Docker) | security-reviewer agent + `tests/test_security.py` | pass: 0 critical/high. Fixed: DNS rebinding (Host allowlist), cross-site writes (Origin check), IDS entity expansion (DOCTYPE rejected), root container, missing nginx headers. Then: `/copilot/query` limited to 1 in flight + 10/min (429 `copilot_busy`, D-26). nginx CSP enforced, same-origin only (D-27): viewer loads cold and cached, 0 violations. Open (low): no disk quota |
| 17 | BCF 3.0 export (`format=bcf`, API + CLI + UI button) | `tests/test_bcf.py`, `test_api`, `test_cli`; XSD check against buildingSMART release_3_0 schemas | pass (project, version, markup, viewpoint all XSD-valid). **Not opened** in BIMcollab Zoom / Solibri yet |
| 18 | End-user test on real Revit ARC/STR models (civil-engineer walkthrough) + 15 popular/heavy samples benchmarked | `docs/user-test.md`, `benchmarks/RESULTS-popular.md`, `benchmarks/RESULTS-heavy.md` | pass (2026-11-11) after 3 fixes (D-49): certificate button, copilot timeout, coordination rounding. BCF not opened in a GUI tool; no outside pilot user |
| 19 | Revit hand-off: BCF 2.1 export + Revit ElementId as `AuthoringToolId` (D-50) | `tests/test_bcf.py`, `tests/test_extract.py`; buildingSMART XSD check of both versions on `Ifc4_Revit_ARC.ifc` | pass (404/404 topic files XSD-valid, 202/202 viewpoints carry the ElementId). **Not imported into Revit** with an add-in yet |

Missing from the repo: `docs/PROPOSAL.md` (original brief was never saved).
