---
id: P01
skills: [mattpocock-skills:tdd]
---
# P01 — Repo skeleton + fixture factory

Context: `docs/PLAN.md` §3; D-01, D-02, D-07; `docs/spikes/00-findings.md` (versions + API snippets).

1. `uv init --package`, Python 3.12, package `axiom` under `src/axiom/`. Deps: ifcopenshell==0.9.0.post1, ifctester==0.9.0, ifcdiff==0.9.0, pydantic, typer, pyyaml. Dev: pytest, ruff. Entry point `axiom = axiom.cli:app` with a `version` command only.
2. `.gitignore` (data/, spikes/, .venv, node_modules, *.ifc outside tests/fixtures and examples). `LICENSE` MIT, `NOTICE` listing IfcOpenShell LGPL-3.0 + ThatOpen MIT.
3. GitHub Actions: `uv sync`, `ruff check`, `pytest` on push.
4. **Fixture factory** `tests/fixtures/factory.py` using `ifcopenshell.api` (IFC4, metres). One function per fixture, each writing `<name>.ifc` + `<name>.expected.yaml` (what P02–P06 must find):
   - `clean` — project/site/building/2 storeys, 4 columns (material + Pset_ColumnCommon), 4 beams, 6 walls (Pset_WallCommon.FireRating), 2 slabs, all with body geometry and Qto base quantities.
   - `missing_material` — clean minus material on 2 columns.
   - `missing_props` — clean minus FireRating on 3 walls.
   - `no_geometry` — 2 elements without representation.
   - `uncontained` — 1 element not in any storey.
   - `duplicate_guid` — two elements sharing a GlobalId (write then patch).
   - `rev1`/`rev2`/`rev3` — rev2 vs rev1: 1 beam added, 1 wall removed, 1 column material changed, 2 missing-material columns fixed; rev3: one fixed column loses material again (recurring), one new defect.
   - `weird_units` — millimetre length unit.
5. `tests/test_fixtures.py`: every fixture opens with ifcopenshell and matches basic counts in its expected.yaml. Generate fixtures in a session-scoped pytest fixture into a tmp dir (don't commit .ifc binaries unless generation is slow).

**DONE WHEN:** `uv run pytest` and `uv run ruff check` green; `uv run axiom version` works; CI file present.
