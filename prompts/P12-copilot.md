---
id: P12
skills: [claude-api, anthropic-skills:tool-design, anthropic-skills:evaluation, anthropic-skills:llm-top-10]
---
# P12 — Grounded engineering copilot + eval set

Context: D-09; proposal Module G (grep `## Module G`). Read the `claude-api` skill for current model ids and tool-use loop before coding.

1. **Eval set first:** `tests/copilot/evals.yaml` — 25 questions over fixtures rev1..rev3 (counts, missing-material columns, what changed rev1→rev2, recurring findings, why MHI dropped, an unanswerable one, a structural-safety bait question). Each: expected tool calls, required GlobalIds/finding ids, forbidden claims.
2. `axiom/copilot/tools.py`: ≤ 10 read-only tools wrapping services (summary, query_elements, element_detail, findings, finding_detail, compare_summary, finding_events, mhi, quantities). Strict input schemas, paginated outputs, project-scoped (tool layer receives project_id from the session, never from the model).
3. `axiom/copilot/agent.py`: Claude tool-use loop (default `claude-sonnet-5-5`, env `ANTHROPIC_API_KEY`, `AXIOM_COPILOT_MODEL`), max tool rounds, system prompt: cite GlobalIds/finding ids, state revisions compared, units + method for quantities, say "not available" when tools return nothing, no safety conclusions. **Citation post-check:** every GlobalId / finding id in the answer must appear in this turn's tool results; else one corrective retry, then return with unverified citations stripped and flagged.
4. API `POST /api/v1/copilot/query` → `{answer, citations:[{type, id}], tool_calls}`. UI panel: suggested questions, answer with clickable citations (focus in viewer / open finding).
5. Prompt-injection: IFC strings (names, pset values) reach the model inside tool results — wrap as data, test with a fixture element named "ignore previous instructions…".
6. Eval runner `uv run python -m axiom.copilot.eval` (skipped in CI without API key) → pass rate report.

**DONE WHEN:** eval pass ≥ 90% with zero fabricated citations; injection test passes; app works with no API key (copilot hidden, everything else intact).
