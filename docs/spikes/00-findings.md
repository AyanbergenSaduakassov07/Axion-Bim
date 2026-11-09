# P00 spike findings — 2026-11-09

Sample: `Ifc4_SampleHouse.ifc` (2.27 MB, IFC4, Revit 2015 via xBIM, 67 IfcElement) from github.com/youshengCode/IfcSampleFiles — **repo has no license: local use only, never commit or redistribute.** Find a licensed public model for benchmarks/README in P13.
Spike code copied to `docs/spikes/` (s1_parse.py, s2_ids.py, s3_diff.py, req.ids, viewer/).

## Go / no-go

| Item | Result | Verdict |
|---|---|---|
| ifcopenshell 0.9.0.post1 on Python 3.12 (uv) | open 0.27 s, all psets of 67 elements read instantly | GO |
| ifctester 0.9.0 IDS | validate 1 ms; per-requirement failures with element + reason | GO (with adapter rules below) |
| ifcdiff 0.9.0 | correct (1 deleted, 1 pset change) but 7.2 s on 67 elements, dominated by geometry | GO as optional cross-check only — D-03 confirmed |
| ThatOpen 3.6 viewer | load 438 ms; click → GlobalId; GlobalId → highlight + fit; unknown GUID detected | GO |

## Pinned versions that work together
- Python: `ifcopenshell==0.9.0.post1 ifctester==0.9.0 ifcdiff==0.9.0`, Python 3.12.
- Web: `three@0.182.0` (fragments peer requires >=0.182), `@thatopen/components@3.6.0`, `@thatopen/fragments@3.6.1`, **`web-ifc@0.0.77`** — 0.0.78 breaks (`StreamMeshes called with 4 arguments, expected 3`). Serve `web-ifc.wasm` + `web-ifc-mt.wasm` and `fragments/dist/Worker/worker.mjs` locally; no unpkg at runtime.
- After changing web-ifc, restart Vite with `--force` (stale prebundle → wasm LinkError `__cxa_throw`).

## API notes

### Python extraction (s1)
- `ifcopenshell.util.unit.calculate_unit_scale(f)` → 0.001 for this file although unit Name is `METRE` (Prefix MILLI). Always use the util, never the Name.
- `ifcopenshell.util.element.get_psets(e)` returns qto sets too (e.g. `BaseQuantities`) and injects an `id` key into every dict → strip `id`; distinguish psets from qtos via `get_psets(e, psets_only=True)` / `qtos_only=True`.
- `get_material(e)` returns IfcMaterialList / IfcMaterialLayerSetUsage etc. → flatten with `ifcopenshell.util.element.get_materials(e)` for names; keep the kind.
- `get_container(e)` gives the storey directly.
- **Real defect found:** slab `BaseQuantities.GrossVolume = 68713.56` while Revit `Dimensions.Volume = 68.71` (m³) → ×1000 inconsistency in exported Qto. Candidate rule **QTO-002 quantity plausibility / unit consistency** (Qto vs geometry within tolerance; flag orders-of-magnitude mismatch). Exactly the evidence-backed finding Axiom should surface.

### IfcTester (s2) — adapter rules for P04
- Python objects: `specs = ids.open(path, validate=True); specs.validate(ifc)`; per spec `s.status`, `s.applicable_entities`; per requirement `r.status`, `r.failures` = list of `{"element": entity, "reason": str}`; `r.passed_entities` exists (JSON reporter has `passed_entities`). `reporter.Json(specs).report()` → `.to_string()`.
- **Zero applicable entities ⇒ `status True`.** Adapter must emit `not_applicable` (unless applicability `minOccurs>=1`, where IDS itself should fail — verify in P04 conformance tests).
- **Entity facet is exact-class:** `IFCWALL` checked 3 IfcWall, ignored 2 IfcWallStandardCase. Axiom adds a coverage hint: "N elements of subtypes not covered by spec X". Differentiator, cheap.
- Failure `reason` is free text — store verbatim as `actual`, facet label (`Pset_WallCommon.FireRating`) as `expected` key.

### IfcDiff (s3)
- Constructor takes **opened files**, not paths: `IfcDiff(old_f, new_f, relationships=[...], is_shallow=True)`; `.diff()`; results in `.added_elements`, `.deleted_elements`, `.change_register[guid] = {"properties_changed": {deepdiff...}}`.

### Viewer (viewer/main.ts)
- `fragments.init(workerUrl)`; `ifcLoader.setup({autoSetWasm:false, wasm:{path:"/wasm/", absolute:true}})`; `ifcLoader.load(uint8, true, name)` returns the FragmentsModel.
- GlobalId → `model.getLocalIdsByGuids([g])`; reverse `model.getGuidsByLocalIds([id])`; geometry check `model.getItemsIdsWithGeometry()`; `model.highlight(ids, MaterialDefinition)` / `resetHighlight`; `camera.controls.fitToBox(await model.getMergedBox(ids), true)`; click → `model.raycast({camera, mouse, dom})` → `localId`. Call `fragments.core.update(true)` after visual changes.
- **localId == IFC STEP id** (33951 == ifcopenshell `.id()`). Contract stays GlobalId (STEP ids aren't stable across revisions), but STEP id disambiguates duplicate-GlobalId elements → store `step_id` on Element.
- fitToBox on a single element frames too tight → add padding / offset view in P10.

## Timings appendix (append P02/P10 measurements here)
| Step | Model | Time |
|---|---|---|
| ifcopenshell open | SampleHouse 2.27 MB | 0.27 s |
| IDS 3 specs | SampleHouse | 0.001 s |
| IfcDiff w/ geometry | SampleHouse | 7.2 s |
| Viewer IFC→fragments load | SampleHouse | 0.44 s |

## Appendix — P02 extraction timing (2026-11-09)

| Model | Size | Elements | `axiom inspect` (extract + profile, no geometry) |
|---|---|---|---|
| Ifc4_SampleHouse.ifc (Revit 2015, mm) | 2.27 MB | 60 | 0.05 s |
| Fixtures (16 elements) | ~40 KB | 16 | < 0.01 s each |

Observation for P03: the sample's 2 `IfcCurtainWall` have no own representation; geometry sits on aggregated members/plates. The geometry-presence rule must treat an aggregate parent with geometric children as satisfied, or it produces false positives on every curtain wall, stair and roof assembly.

## Appendix — P10 viewer load (2026-11-09)

Apple M5, Playwright Chromium, Vite dev server, `window.__axiomViewer.stats` (load = fetch IFC + convert in worker + load fragments + fit camera).

| Model | IFC | Fragments | Cold load (convert) | Warm load (IndexedDB) | JS heap after load |
|---|---|---|---|---|---|
| Ifc4_SampleHouse.ifc | 2.27 MB | 202 kB | 1.90 s | 1.36 s | 112 MB (148 MB after 10 focus ops) |
| Fixture rev1 (16 elements) | ~40 KB | — | < 1 s | — | — |

Finding → element on SampleHouse: 10/10 finding rows focused the same GlobalId. Both curtain walls (aggregate, no own representation) return `no_geometry`; the UI says "Element has no renderable geometry." The warm path still pays fragments worker start-up and camera fit, so caching saves conversion (~0.5 s here) and will matter more on large models.
