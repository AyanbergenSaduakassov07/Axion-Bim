---
id: P08
skills: [mattpocock-skills:tdd]
---
# P08 — FastAPI + subprocess job runner

Context: D-05, D-06; PLAN §3 diagram; proposal §13 routes (grep `# 13. API design`), §14 security.

1. `axiom/jobs/`: `jobs` table (id, kind, payload_json, status queued|running|done|error, progress, error_message, timestamps). Runner: a single background thread in the API process pulls queued jobs and executes each in a **child process** (`multiprocessing` spawn) with `resource.setrlimit(RLIMIT_AS)` + wall-clock timeout from settings. Child crash/timeout → job `error` with a user-safe message; full detail in logs. On API start, `running` jobs from a dead process → `error`.
2. `axiom/api/`: FastAPI app factory, settings via pydantic-settings (`AXIOM_DB_URL`, `AXIOM_DATA_DIR`, `AXIOM_MAX_UPLOAD_MB`, `AXIOM_JOB_TIMEOUT_S`, `AXIOM_JOB_MEM_MB`). Routes (v1 prefix `/api/v1`): projects CRUD-lite, models, `POST /models/{id}/revisions` (multipart upload → validate extension + `ISO-10303-21` header + size → store → enqueue pipeline job → 202 with job id), `GET /jobs/{id}`, revision summary/elements (paginated, filter by class/storey/search)/element by GlobalId, audits + findings (filter status/severity/category/rule) + health-index, comparisons + changes + finding events, quantities, `POST /ids` upload. Routes call services only.
3. Structured errors: `{error: {code, message}}`; never leak paths or tracebacks.
4. Export OpenAPI to `apps/web/src/api/openapi.json` via a script; document `npx openapi-typescript` generation (P09 consumes).
5. Tests: httpx TestClient — upload rev1 then rev2 → poll jobs → findings + comparison endpoints return golden data; oversized/non-IFC upload rejected; a job that exceeds timeout ends `error`; a forced child segfault (`os.abort()` in a test-only job kind) ends `error` and API stays up.

**DONE WHEN:** tests green; `uv run axiom serve` starts and `/docs` shows the API.
