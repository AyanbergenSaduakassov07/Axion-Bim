# Axiom BIM — Limitations and Scope

This document records the intentional design boundaries, known trade-offs, and out-of-scope capabilities for Axiom BIM v1.

---

## 1. Model Health Index (MHI) is NOT a Safety Rating

- **Information Deficiency vs Structural Integrity:**
  MHI measures information completeness, schema conformance, property presence, and metadata compliance. A low score or a rule violation indicates missing or non-compliant data (an *information deficiency*). It does **not** evaluate structural capacity, load-bearing adequacy, code compliance, fire-resistance calculations, or physical safety.
- **No Structural Judgments:**
  Axiom BIM never reports that a building or element is "safe", "structurally sound", "unsafe", or "will collapse". Calculations are strictly bounded to metadata verification, IDS specification checks, and geometric volume/area measurements.

---

## 2. Element Identity & Matching

- **Strict GlobalId-Based Tracking:**
  Revisions are matched strictly by IFC `GlobalId` (22-character IFC GUID format).
- **No Heuristic Matching in v1:**
  If an authoring tool (e.g. Revit, ArchiCAD, Tekla) re-exports an existing building element with newly generated GlobalIds, Axiom classifies those elements as removed and added rather than modified. Heuristic spatial or property-based element matching (e.g. nearest-centroid, matching mark/tag) is explicitly deferred to future releases.
- **De-duplication Scope:**
  Duplicate GlobalIds within a single model revision are flagged as rule violations (`GEO-002`) with the duplicate instances recorded in evidence.

---

## 3. Geometry Checks & Engine Scope

- **Representation Inspection:**
  Geometry verification focuses on presence of representation (`GEO-001`), axis placement (`SPA-001`), storey containment (`SPA-002`), and bounding-box / boundary-representation volume extraction via IfcOpenShell.
- **No Heavy Clash Detection:**
  Axiom does not execute multi-discipline spatial interference / clash detection between trade models (MEP vs Structural vs Architectural).
- **Quantity Methods:**
  Quantities are distinguished between:
  - `qto`: Summed directly from explicit IFC quantity sets (`Qto_*`).
  - `geometry`: Measured directly from tessellated / boundary geometry via IfcOpenShell shape geometry.
  Where explicit quantities differ from geometric measurements, both methods and units are disclosed.

---

## 4. Single-User & Local Deployment

- **No Multi-Tenant Authentication:**
  Designed for local-first single-user workflows. The API runs without authentication or per-user rate limits (the copilot alone is capped: one question at a time, 10 per minute, per process); deploying to an untrusted public network requires placing it behind a reverse proxy with authentication and rate limiting. The API answers only to `Host` names in `AXIOM_ALLOWED_HOSTS` (default `localhost,127.0.0.1,::1,testserver`) and rejects state-changing requests from other origins; add a LAN hostname there to reach it from another machine.
- **SQLite Single-Writer Concurrency:**
  Data persistence uses SQLite with SQLAlchemy Core and write-ahead logging (WAL). Concurrent write access is managed via the subprocess job runner queue rather than distributed queues (e.g. Celery / Redis).
