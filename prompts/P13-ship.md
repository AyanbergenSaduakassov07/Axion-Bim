---
id: P13
skills: [security-reviewer, ponytail:ponytail-audit, anthropic-skills:anti-slop-writing]
---
# P13 — Hardening, benchmarks, README, demo

Context: proposal §15 benchmarks, §19 definition of success (grep `# 19.`), §21 portfolio.

1. Security: run the `security-reviewer` agent over upload, job runner, file serving, copilot. Fix critical/high. Check path traversal on file serving, upload limits, XML/IDS parsing (defusedxml or ifctester's parser hardening), CORS locked to the web origin.
2. `/ponytail-audit` → delete dead code and unused deps.
3. Benchmarks `benchmarks/run.py` on 3–5 public IFC models of increasing size (record source + license in `examples/models/SOURCES.md`): file size, elements, extract time, audit time, compare time, peak RSS, viewer load time. Output `benchmarks/RESULTS.md`. No comparisons to commercial tools.
4. `docker-compose.yml` (api + web) for one-command run; `uv run axiom serve` remains the dev path.
5. README: one-paragraph thesis, 3 screenshots + GIF, the §19 scenario as a walkthrough, `axiom compare` CLI example, architecture diagram from PLAN §3, limitations (`docs/limitations.md`: MHI is not a safety rating, heuristic matching absent, geometry checks scope), license/NOTICE.
6. Demo script `docs/demo-script.md` for the 2–3 min video (proposal §21 order).
7. Walk proposal §19 steps 1–13 on two different models; record pass/fail per step honestly in `docs/release-check.md`.

**DONE WHEN:** release-check has every step passing on 2 models, or the failures are listed as known limitations.
