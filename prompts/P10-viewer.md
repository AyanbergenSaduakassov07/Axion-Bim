---
id: P10
skills: [anthropic-skills:ui-ux-pro-max]
---
# P10 — 3D Model Explorer + finding → element

Context: `docs/spikes/00-findings.md` item 4 (working ThatOpen snippets, GlobalId mapping); D-08. Check context7 for the pinned ThatOpen version before coding.

1. `apps/web/src/viewer/`: the only module importing ThatOpen. API: `load(revisionFileUrl)`, `highlight(globalIds, style)`, `focus(globalId)`, `isolate(globalIds)`, `setClassVisibility(cls, bool)`, `onSelect(cb: (globalId) => void)`. Backend serves the stored IFC at `GET /api/v1/revisions/{id}/file`. Convert to Fragments in a web worker; cache the fragments per file hash (IndexedDB, try/catch, works without it).
2. **Model Explorer** page: left = spatial tree + class filters (data from backend, not viewer); center = viewport; right = element panel (properties, quantities, findings for that element — all from backend by GlobalId).
3. Quality Center integration: selecting a finding → `focus` + highlight affected GlobalId + detail drawer; findings tab can "highlight all" for the current filter (color by severity).
4. GlobalId not found in viewer (e.g. no geometry) → explicit message "element has no renderable geometry", never silent.
5. Performance: measure load time + memory on the P00 public sample; note in `docs/spikes/00-findings.md` appendix.
6. Playwright: click finding row → viewer reports focused GlobalId equals the finding's GlobalId (expose a test hook on `window.__axiomViewer` in dev only).

**DONE WHEN:** e2e green; the finding→element interaction works on both a fixture and the public sample.
