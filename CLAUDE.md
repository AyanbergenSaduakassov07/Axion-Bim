# Axiom BIM

IFC model intelligence: extract → validate (IDS + Python rules) → score (MHI) → compare revisions → investigate in 3D → grounded copilot.

## Rules that apply to every task
- Backend is the source of truth. The viewer renders; the LLM explains. Neither computes engineering results.
- Never report `pass` for something not evaluated. Statuses: `pass|fail|warning|not_applicable|not_evaluated|error`. Revision events: `new|resolved|persistent|recurring|changed|uncertain`. Do not mix vocabularies.
- Every finding carries GlobalId, rule id + version, expected, actual, evidence. Every quantity carries unit + method (`qto|geometry`).
- Missing information is an information deficiency, never "unsafe". No structural-safety language anywhere.
- Layers: `api/` → `services/` → `repo/`. Routes never touch the DB. CLI uses the same services.
- IFC processing never runs in a request handler; it runs in the subprocess job runner.
- Tests: fixtures come from `tests/fixtures/factory.py` with `expected.yaml`. New logic = a failing test first.
- Pin library versions; check context7 before writing against ThatOpen, ifcopenshell, ifctester APIs.

## Stack
Python 3.12 · uv · ifcopenshell/ifctester/ifcdiff 0.9 · FastAPI · Pydantic v2 · SQLAlchemy Core + Alembic · SQLite · pytest · ruff.
Web: Vite · React · TS · Tailwind · TanStack Query · @thatopen/components 3.x · web-ifc.

## Queue
`/next` runs the next ready prompt; `/status` shows progress. Queue and status live in `prompts/INDEX.md`.

## Docs map (grep a heading, read only that section)
- `docs/PLAN.md` — verdict, architecture (§3), entities, finding identity, MHI formula, milestones, risks
- `docs/DECISIONS.md` — D-01…; append new decisions here
- `docs/PROPOSAL.md` — original product brief (large; grep `^#` first)
