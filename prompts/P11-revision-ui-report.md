---
id: P11
skills: [anthropic-skills:ui-ux-pro-max, dataviz]
---
# P11 — Revision Intelligence UI + reports

Context: proposal Module D "Revision report" + Module H (grep `## Module H`); D-10.

1. **Revisions** page: timeline of revisions with MHI sparkline; pick old/new → summary (added/removed/modified by class), property-change table (GlobalId, path, old → new), finding events grouped new / resolved / recurring / persistent / changed / uncertain (recurring visually prominent), MHI delta waterfall by dimension, impact list. `identity_unstable` comparisons show a banner and no fake continuity.
2. Viewer: "show changes" mode colors added/modified/removed-ghost (removed from old file if loaded) and finding events.
3. **Quantities** page: grouped tables with method column; revision delta column.
4. `axiom/report/`: canonical JSON (audit + MHI + optional comparison + reproducibility block), CSV findings, HTML via one Jinja2 template (print CSS so browser "Save as PDF" is clean). API `POST /audits/{id}/reports?format=json|csv|html`, CLI `axiom report`.
5. Test: report JSON of rev1→rev2 matches a golden file (normalize timestamps/ids); HTML renders without external network.

**DONE WHEN:** golden report test green; Playwright smoke: open comparison rev2→rev3, recurring finding visible, clicking it focuses the element.
