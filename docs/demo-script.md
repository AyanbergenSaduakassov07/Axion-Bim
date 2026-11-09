# Axiom BIM — 2–3 Minute Demo Video Script

**Target Duration:** 2 minutes 45 seconds
**Format:** Screen recording with voiceover
**Prerequisites:** Pre-seeded or live project with revisions 1–3 (`Revision Tower`)

---

## Shot 1: The Problem & Thesis (00:00 – 00:25)
- **Visual:** Project Dashboard showing revision cards and MHI trendline.
- **Voiceover:**
  > "BIM coordinators and structural engineers spend hours manually verifying IFC submissions across design revisions. Proprietary viewers check clashes, but they don't give you deterministic information tracking, regression analytics, or grounded AI answers.
  > Axiom BIM is an open-source model intelligence platform. It extracts IFC data into normalized snapshots, validates against Information Delivery Specifications and Python rules, scores Model Health, tracks revision regressions, and powers a grounded 3D copilot."

---

## Shot 2: Ingestion & Quality Center (00:25 – 00:55)
- **Visual:** Open Revision 1. Navigate to the **Quality Center**.
- **Actions:**
  - Point to the MHI score gauge (95.18 / 100).
  - Filter findings by severity (`high`) and rule (`MAT-001`).
  - Click **"Highlight in 3D"** on column `C2` (missing material).
  - Viewer smoothly flies to and highlights `C2` in amber with surrounding elements framed.
- **Voiceover:**
  > "Every uploaded IFC runs through an isolated subprocess runner. Built-in rules and IDS specs evaluate elements deterministically. Here in Revision 1, our Model Health Index is 95.18. Column C2 fails rule MAT-001—it lacks a material assignment. One click isolates and highlights the exact element in our Three.js/ThatOpen 3D viewport."

---

## Shot 3: Quantities & Canonical Reports (00:55 – 01:25)
- **Visual:** Switch to **Quantities** tab, then trigger Report Export.
- **Actions:**
  - Show quantity table grouped by class and material.
  - Hover over the QTO vs Geometry comparison badge.
  - Open the printable HTML audit report in a new tab.
- **Voiceover:**
  > "Axiom computes quantities with strict method tracking. We separate quantities extracted from IFC Qto sets from actual geometry-measured volumes. Missing volumes are highlighted explicitly. When an audit report is needed, Axiom generates canonical JSON, CSV, or a clean, printable HTML summary ready for sign-off."

---

## Shot 4: Revision Intelligence & Regressions (01:25 – 02:05)
- **Visual:** Navigate to **Revisions** overview, then open the **Comparison View** between Rev 2 and Rev 3.
- **Actions:**
  - Show the MHI Waterfall step chart (100 -> 96.90).
  - Point to the Change summary: 1 added, 1 modified.
  - Highlight the Finding Events table showing `MAT-001` on column `C2` labeled **`recurring`** in orange, and `STR-WALL` on `W1` labeled **`new`**.
- **Voiceover:**
  > "When the architect sends Revision 2, column C2 is fixed and health hits 100. But in Revision 3, C2's material assignment disappears again. Axiom's revision engine classifies finding lifecycles: new, resolved, persistent, or recurring. Notice MAT-001 on C2 is flagged as recurring—an issue that was resolved, but regressed. The MHI waterfall shows exactly which dimension dropped the score."

---

## Shot 5: Grounded Copilot & Safety Guardrails (02:05 – 02:40)
- **Visual:** Open the **Copilot** panel.
- **Actions:**
  - Type: `"What findings came back in r3 compared to r2?"`
  - Show the response citing `C2 [[el:...]]` and `MAT-001 C2 [[finding:...]]`.
  - Click the `C2` chip to jump directly into the Model Explorer focused on `C2`.
  - Type: `"Is the rev3 structure safe? Will column C2 fail under load?"`
  - Show the response politely refusing structural safety evaluation and explaining it reports information deficiency only.
- **Voiceover:**
  > "The built-in copilot uses read-only tools directly against the database with strict citation verification. It cannot fabricate elements—every citation must have appeared in tool outputs during the turn. Clicking a citation chip immediately navigates to that element in the 3D explorer. And when asked about structural safety, Axiom firmly maintains its boundary: reporting information completeness, never structural engineering judgments."

---

## Shot 6: Wrap-up & CLI (02:40 – 02:45)
- **Visual:** Terminal showing `axiom compare` CLI output, then repo URL.
- **Voiceover:**
  > "Axiom runs locally via Python, CLI, or Docker Compose. Fast, deterministic, and open source under the MIT license. Check it out on GitHub."
