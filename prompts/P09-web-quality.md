---
id: P09
skills: [anthropic-skills:ui-ux-pro-max, dataviz]
---
# P09 — Web shell + Quality Center

Context: proposal §16 UI (grep `# 16. User interface`); PLAN §3. API from P08 (`apps/web/src/api/openapi.json`).

1. `apps/web`: Vite + React + TS + Tailwind + TanStack Query + React Router. Types generated from OpenAPI (`openapi-typescript`), thin fetch client. Design tokens on `:root`: dark graphite workspace, one restrained accent, severity colors accessible in both themes, tabular numerals, dense tables. No gradients, no "AI SaaS" look — it should read like Solibri/engineering software.
2. Screens: **Projects** (list/create) → **Project overview** (latest revision, element count, MHI, findings by severity, revision timeline) → **Upload** (drag-drop, job progress polling, error states).
3. **Quality Center**: MHI header (score, blocked badge, coverage) + per-dimension breakdown bar (contribution, evaluated/passed/failed/not evaluated — `not_evaluated` visually distinct from `fail`); findings table (virtualized, filters: severity/category/rule/status/class, search GlobalId); finding detail drawer (rule, expected vs actual, evidence JSON pretty, rule doc link). Leave a right-side slot for the 3D viewer (P10).
4. Empty, loading and error states for every query. Keyboard navigable table.
5. Playwright smoke test: upload `rev1` fixture → wait job → Quality Center shows the expected finding count.

**DONE WHEN:** smoke test green; screenshots of overview + Quality Center saved to the scratchpad and reviewed for density/hierarchy.
