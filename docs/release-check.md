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
| 14 | Second real-world model end to end in the UI | — | **not run** (SampleHouse timings for the viewer in `docs/spikes/00-findings.md`) |
| 15 | CI on GitHub (`.github/workflows/ci.yml`) | — | **not checked** after push; the web job needs WebGL in headless Chromium |
| 16 | Security review (upload, job runner, file serving, IDS parsing, copilot, Docker) | security-reviewer agent + `tests/test_security.py` | pass: 0 critical/high. Fixed: DNS rebinding (Host allowlist), cross-site writes (Origin check), IDS entity expansion (DOCTYPE rejected), root container, missing nginx headers. Open (low): no rate limit on `/copilot/query`, no SPA CSP, no disk quota |

Missing from the repo: `docs/PROPOSAL.md` (original brief was never saved).
