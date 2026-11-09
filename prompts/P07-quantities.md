---
id: P07
skills: [mattpocock-skills:tdd]
---
# P07 — Quantity intelligence

Context: Proposal Module E (grep `## Module E`). PLAN §3 entity `Quantity(method: qto|geometry)`.

1. `axiom/quantities/`: aggregate Qto-sourced quantities (already extracted in P02) grouped by class / storey / material / classification. Output rows: group, quantity name, total SI value, unit, element count, method, elements missing that quantity.
2. Geometry fallback (opt-in flag `--geometry`): `ifcopenshell.geom` iterator (multiprocess) for volume/area of elements lacking Qto values, via `ifcopenshell.util.shape`. Tag `method=geometry`. Never sum qto and geometry values into one total — report them as separate columns.
3. Revision deltas: quantity totals per group old vs new, using P06 comparisons.
4. CLI `axiom quantities file.ifc [--by storey|class|material] [--geometry]`.
5. Numeric tests: fixture factory geometry has known dimensions (e.g. 0.3×0.3×3.0 m column = 0.27 m³) — geometry-computed and Qto values both match within tolerance; mm-unit fixture gives identical SI totals.

**DONE WHEN:** numeric tests green; mixing methods is impossible by construction (type-level or test).
