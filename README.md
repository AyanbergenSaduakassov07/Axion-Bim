# Axiom BIM

[![CI](https://github.com/ayanbergen/axiom-bim/actions/workflows/ci.yml/badge.svg)](https://github.com/ayanbergen/axiom-bim/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Axiom BIM is an open-source model intelligence engine and web interface for Industry Foundation Classes (IFC) models. It extracts BIM data into normalized SQL snapshots, validates against Information Delivery Specifications (IDS via IfcTester) and deterministic Python rules, scores information completeness transparently via the Model Health Index (MHI), computes and audits quantities with method tagging (`qto` vs `geometry`), tracks finding lifecycles across revisions (*new*, *resolved*, *persistent*, *recurring*), inspects elements in an interactive 3D WebGL viewer (ThatOpen Components), and provides a grounded AI copilot with strict citation verification.

---

## Screenshots

### 1. Quality Center & 3D Element Highlighting
Inspect deterministic rule violations, filter by severity, and isolate affected elements directly in 3D:
![Quality Center & 3D Highlighting](docs/images/quality-3d.png)

### 2. Revision Intelligence & MHI Waterfall
Compare design revisions, analyze finding regressions (*recurring* issues), and trace health deltas:
![Revision Intelligence & MHI Waterfall](docs/images/revisions.png)

### 3. Grounded Copilot with Verified Citations
Query project data via natural language. Citations are verified against backend tool outputs and link directly to the 3D explorer:
![Grounded Copilot](docs/images/copilot.png)

---

## Walkthrough Scenario

Axiom tracks the complete lifecycle of a model across design stages (e.g. `rev1` → `rev2` → `rev3`):

1. **Revision 1 (Initial Ingestion):**
   - Upload `rev1.ifc` and `structural-basic.ids`.
   - The isolated subprocess runner extracts 16 elements, runs 6 built-in checks and IDS specifications.
   - Initial MHI score is **95.18**. Four findings are detected, including `MAT-001` on columns `C2` and `C3` (missing material).
2. **Revision 2 (Fixes & Additions):**
   - Upload `rev2.ifc`. Column `C2` has its material assigned, wall `W6` is added, and beam `B5` is removed.
   - The comparison engine identifies 4 resolved findings. MHI rises to **100.0**.
3. **Revision 3 (Issue Regression):**
   - Upload `rev3.ifc`. Column `C2`'s material assignment is accidentally dropped again during architectural re-export.
   - Axiom flags `MAT-001` on column `C2` as **`recurring`** (an issue that was resolved in `r2` but reappeared in `r3`).
   - MHI falls to **96.90**. The waterfall chart isolates the exact dimension penalty.

For a timed recording outline, see [docs/demo-script.md](docs/demo-script.md). The sample model sources and licenses are documented in [examples/models/SOURCES.md](examples/models/SOURCES.md).

---

## CLI Usage

Axiom exposes the same underlying services through a fast command-line interface:

```bash
# Generate the deterministic three-revision demo models
uv run python scripts/e2e_fixtures.py /tmp/axiom-models

# Inspect and audit the first revision
axiom inspect /tmp/axiom-models/rev1.ifc
axiom audit /tmp/axiom-models/rev1.ifc --ids examples/ids/structural-basic.ids

# Compare all three revisions and classify finding lifecycle events
axiom compare /tmp/axiom-models/rev1.ifc /tmp/axiom-models/rev2.ifc /tmp/axiom-models/rev3.ifc \
  --ids examples/ids/structural-basic.ids

# Replace AUDIT_ID with the number printed by `axiom audit`
axiom report AUDIT_ID --format html --out report.html
```

---

## Architecture

The system maintains strict layer boundaries: `api/` → `services/` → `repo/`. IFC processing and heavy geometry parsing never run within HTTP request threads; all processing runs in a supervised subprocess runner with memory and time caps.

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

---

## Grounded Copilot

The Axiom Copilot (`POST /api/v1/copilot/query`) operates over 9 read-only backend tools. Every citation in the generated response (`[[el:<GlobalId>]]` or `[[finding:<key>]]`) is verified by a strict post-check ensuring the token was present in that turn's tool output.

- **Credentials:** Requires either `ANTHROPIC_API_KEY` (defaulting to `claude-sonnet-5-5`) or `OPENROUTER_API_KEY` (using Messages-compatible free models, e.g. `nvidia/nemotron-3-ultra-550b-a55b:free`).
- **No-Key Fallback:** Without an API key, the copilot panel is cleanly hidden in the UI and queries return 503 `copilot_unavailable`. All core inspection, audit, diffing, and 3D features remain fully operational.
- **Measured Eval Score:** Evaluated on the 25-case deterministic eval set (`tests/copilot/evals.yaml`). On the free OpenRouter model (`nvidia/nemotron-3-ultra-550b-a55b:free`), 6 questions ran before daily rate limit (50 req/day): **4/6 passed (67%), 0 fabricated citations**. See [docs/DECISIONS.md](docs/DECISIONS.md#d-22--grounded-copilot-p12) for details.

---

## Quickstart

### Option A: Local Development
```bash
# 1. Install backend dependencies (Python 3.12 + uv)
uv sync

# 2. Run migrations and start API server
uv run axiom serve --port 8000

# 3. In another terminal, start the web interface
cd apps/web
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173).

### Option B: Docker Compose
```bash
docker compose up --build
```
Open [http://localhost:3000](http://localhost:3000) (API at [http://localhost:8000](http://localhost:8000)).

---

## Verification & Testing

Every commit passes the complete verification suite:

```bash
# Backend test suite (178 passed, 1 xfailed)
uv run pytest -q

# Code style and linting
uv run ruff check src tests

# Web typecheck, production build, unit tests, and Playwright E2E
cd apps/web
npm run typecheck
npm run build
npm test
npx playwright test
```

---

## Limitations

Please review [docs/limitations.md](docs/limitations.md) for architectural scope:
- **MHI is not a safety rating:** MHI quantifies data completeness and information compliance; it does not measure structural capacity, load safety, or code compliance.
- **GlobalId matching:** Revision comparison tracks elements strictly by IFC `GlobalId` without heuristic matching.
- **Geometry scope:** Representation validation and volume extraction; full spatial clash detection is deferred to v2.

---

## License & Notice

Axiom BIM is licensed under the [MIT License](LICENSE).
Third-party dependencies and LGPL compliance for IfcOpenShell are detailed in [NOTICE](NOTICE).
