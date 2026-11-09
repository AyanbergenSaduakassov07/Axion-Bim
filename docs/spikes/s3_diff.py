"""Spike 3: IfcDiff on sample vs copy with one property edited + one element removed."""
import sys, time, ifcopenshell, ifcopenshell.api, ifcopenshell.util.element as ue
from ifcdiff import IfcDiff

src = sys.argv[1]
old = ifcopenshell.open(src); new = ifcopenshell.open(src)
wall = new.by_type("IfcWall")[0]
pset = new.by_id(ue.get_psets(wall)["Pset_WallCommon"]["id"])
ifcopenshell.api.run("pset.edit_pset", new, pset=pset, properties={"IsExternal": False})
ifcopenshell.api.run("root.remove_product", new, product=new.by_type("IfcFurniture")[0])
new.write("new.ifc")
t = time.perf_counter()
d = IfcDiff(ifcopenshell.open(src), ifcopenshell.open("new.ifc"), relationships=["property","attributes","container","geometry"])
d.diff()
print("diff_s", round(time.perf_counter() - t, 3))
print("added", len(d.added_elements), "deleted", len(d.deleted_elements), "changed", len(d.change_register))
for gid, ch in list(d.change_register.items())[:3]:
    print(gid, ch)
