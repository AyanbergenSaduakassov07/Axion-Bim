"""Spike 1: parse sample, units, counts, 5 elements with psets/material."""
import sys, time, collections
import ifcopenshell, ifcopenshell.util.element as ue, ifcopenshell.util.unit as uu

t = time.perf_counter()
f = ifcopenshell.open(sys.argv[1])
t_open = time.perf_counter() - t
print("schema", f.schema, "open_s", round(t_open, 3))
print("length unit scale (to m):", uu.calculate_unit_scale(f))
proj = f.by_type("IfcProject")[0]
print("project", proj.Name, [u.UnitType + ":" + str(getattr(u, "Name", "")) for u in proj.UnitsInContext.Units[:6]])
elems = f.by_type("IfcElement")
print("elements", len(elems))
print(collections.Counter(e.is_a() for e in elems).most_common(12))
for e in [x for x in elems if x.is_a() in ("IfcWall", "IfcWallStandardCase", "IfcSlab", "IfcColumn", "IfcBeam", "IfcDoor")][:5]:
    mat = ue.get_material(e)
    print("--", e.GlobalId, e.is_a(), e.Name, "| container:", getattr(ue.get_container(e), "Name", None),
          "| material:", mat.is_a() if mat else None, "| has_repr:", e.Representation is not None)
    for pset, props in ue.get_psets(e).items():
        print("   ", pset, {k: v for k, v in list(props.items())[:4]})
t = time.perf_counter()
n = sum(len(ue.get_psets(e)) for e in elems)
print("all psets read:", n, "s", round(time.perf_counter() - t, 3))
