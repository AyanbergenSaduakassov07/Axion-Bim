# End-user test: a civil engineer reviews a real delivery

**Date:** 2026-11-11.
**Build:** `feat/ru-copilot-chat`, after D-48.
**Who:** the developer acting as a BIM coordinator on a design-stage review (not an outside pilot user).
**Setup:** web app (Vite dev server and API) on a fresh data directory, Chromium driven by Playwright.

**Models:** buildingSMART certification samples:
- `Ifc4_Revit_ARC.ifc` and `Ifc4_Revit_ARC_FireRatingAdded.ifc` (a real revision pair).
- `Ifc4_Revit_STR.ifc`.
- `examples/ids/structural-basic.ids` as the client requirements file.

**Scenario:** an office building with Architecture and Structure models. The client requires walls to carry
`FireRating`. The architect delivers r1, gets the issue list, and fixes the walls in r2.

## Results

| # | Step (what an engineer does) | Result | Notes |
|---|---|---|---|
| 1 | Create project, two discipline models, add the client IDS once | pass | IDS becomes the default for uploads (★) |
| 2 | Upload Revit STR (11.3 MB, 4,150 elements) with the geometry pass | pass | Job done; Quality Center link appears |
| 3 | Upload Revit ARC r1, then the FireRatingAdded file as r2 | pass | 6.3 s each in the UI, including geometry |
| 4 | Quality Center on r1: decision, MHI, dimensions, issues by rule | pass | Accepted with comments, MHI 81.1. 47 walls fail `IDS:STR-WALL` (no FireRating), 2 slabs fail MAT-001, 47 walls fail QTO-002 |
| 5 | Open a finding: expected / actual / evidence / GlobalId, 3D focus | pass | Wall highlighted in the viewer; evidence lists both quantity values (see finding A) |
| 6 | Bulk-assign the 2 slab findings: in progress, "Structural lead", due date | pass | Rows show state, assignee and due date. The dashboard counts 2 overdue |
| 7 | Issue a delivery certificate | **fail → fixed** | Button stayed disabled after typing a name until a reload (D-49). After the fix it is issued at once with a sha256 |
| 8 | Compare r1 → r2 | pass | MHI +15.8 (81.1 → 96.9), 51 elements modified, 42 resolved, 0 new, 207 persistent |
| 9 | Quantities by class, methods kept apart, Δ vs previous revision | pass | qto and geometry totals in separate rows with units; CSV export offered |
| 10 | Project coordination across Architecture and Structure | pass | Units agree (mm). Georeferencing fails (finding B). Storey levels `not evaluated`: the STR file has no storeys |
| 11 | Export BCF 3.0 and the printable HTML report | pass | BCF: 207 topics, 624 files in the zip. HTML shows the decision and the "not a structural assessment" note |
| 12 | Switch the UI to Russian and Kazakh | pass | Dashboard and labels translated; IFC names and rule ids kept as is |
| 13 | Ask the copilot: "Which walls are still missing a FireRating in r2?" | **fail → fixed** | The free OpenRouter model held the request for over 3 min with no feedback. Now a 60 s timeout returns `copilot_unavailable` (D-49). No answer quality was measured |
| 14 | Browser console on every page (quality, revisions, 3D, quantities, project) | pass | 0 errors on clean loads |
| 15 | Read the coordination panel as an engineer | **friction → fixed** | "2.70000000000008 m" and 15-digit coordinates; now rounded for display (D-49) |

## What the engineer would act on

- **A. Duplicate, inconsistent wall quantities.** Revit wrote `Qto_WallBaseQuantities.NetVolume` twice per wall:
  8.4 × 10⁹ (mm³, although the file declares m³) and 4.52 m³. QTO-002 flags all 47 walls, and the evidence
  shows the ratio (1.9 × 10⁹). Anyone taking volumes from this file for a bill of quantities would be wrong by
  nine orders of magnitude. This is an exporter defect, not an Axiom one.
- **B. ARC and STR are not georeferenced to the same site.** Their reference latitudes differ by 2.6°
  (≈ 290 km). Federating these models in a coordination tool would place them apart.
- **C. The fix is visible.** r2 resolves 42 of 47 `FireRating` findings. Five walls are still missing it, so the
  architect needs one more round before the stage can be closed with no open IDS findings.

## Not covered

- No outside engineer has used it yet; this walkthrough is the developer's.
- The BCF was not opened in BIMcollab, Solibri or Revit (only XSD-validated, release-check row 17).
- The Kazakh text has not been reviewed by a native speaker.
- Copilot answer quality on the free model is unproven. The live eval run on 2026-11-11 hit provider errors
  and missed tools; the ≥ 90 % target needs a paid model.
- Kazakh number grouping showed "4,259" in the test Chromium (reduced ICU data). Node and full Chrome give
  "4 259".

The models for this walkthrough are kept locally in the gitignored `demo/` folder; see the README's Demo section.
