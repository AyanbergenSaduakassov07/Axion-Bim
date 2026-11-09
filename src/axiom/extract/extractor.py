"""IFC file -> Snapshot. Relations are resolved via ifcopenshell.util, never hand-walked."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.classification as uc
import ifcopenshell.util.element as ue
import ifcopenshell.util.unit as uu

from axiom.extract.snapshot import (
    ClassificationRef,
    Element,
    MaterialRef,
    PropertyValue,
    Quantity,
    RevisionMeta,
    Scalar,
    Snapshot,
    SpatialNode,
)

log = logging.getLogger(__name__)
# Subtraction features (openings, voids) are geometry operations, not model elements users audit.
EXCLUDED_CLASSES = ("IfcFeatureElementSubtraction",)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract(path: str | Path) -> Snapshot:
    path = Path(path)
    f = ifcopenshell.open(str(path))
    length_scale = uu.calculate_unit_scale(f)
    elements = tuple(
        _element(f, el) for el in f.by_type("IfcElement") if not any(el.is_a(c) for c in EXCLUDED_CLASSES)
    )
    log.info("extracted %d elements from %s", len(elements), path.name)
    return Snapshot(meta=_meta(f, path, length_scale), spatial=_spatial(f, length_scale), elements=elements)


def _meta(f: ifcopenshell.file, path: Path, length_scale: float) -> RevisionMeta:
    projects = f.by_type("IfcProject")
    apps = [a.ApplicationFullName for a in f.by_type("IfcApplication") if a.ApplicationFullName]
    assignment = uu.get_unit_assignment(f)
    units = {
        u.UnitType: uu.get_full_unit_name(u)
        for u in (assignment.Units if assignment else ())
        if hasattr(u, "UnitType") and u.is_a("IfcNamedUnit")
    }
    return RevisionMeta(
        schema_name=f.schema,
        length_scale=length_scale,
        units=units,
        authoring_app=apps[0] if apps else (f.header.file_name.originating_system or None),
        project_name=projects[0].Name if projects else None,
        georef=_georef(f),
        file_sha256=file_sha256(path),
        file_size=path.stat().st_size,
    )


def _georef(f: ifcopenshell.file) -> dict[str, Scalar] | None:
    if f.schema != "IFC2X3" and (conv := f.by_type("IfcMapConversion")):
        c = conv[0]
        crs = c.TargetCRS.Name if c.TargetCRS else None
        return {
            "crs": crs,
            "eastings": c.Eastings,
            "northings": c.Northings,
            "orthogonal_height": c.OrthogonalHeight,
            "scale": c.Scale,
        }
    sites = [s for s in f.by_type("IfcSite") if s.RefLatitude and s.RefLongitude]
    if not sites:
        return None
    return {"ref_latitude": _dms(sites[0].RefLatitude), "ref_longitude": _dms(sites[0].RefLongitude)}


def _dms(parts) -> float:
    return sum(float(v) / 60**i for i, v in enumerate(parts))


def _spatial(f: ifcopenshell.file, length_scale: float) -> tuple[SpatialNode, ...]:
    nodes = []
    for el in [*f.by_type("IfcProject"), *f.by_type("IfcSpatialStructureElement")]:
        parent = ue.get_aggregate(el)
        elevation = getattr(el, "Elevation", None) if el.is_a("IfcBuildingStorey") else None
        nodes.append(
            SpatialNode(
                global_id=el.GlobalId,
                ifc_class=el.is_a(),
                name=el.Name,
                parent_global_id=parent.GlobalId if parent else None,
                elevation_m=elevation * length_scale if elevation is not None else None,
            )
        )
    return tuple(nodes)


def _element(f: ifcopenshell.file, el: ifcopenshell.entity_instance) -> Element:
    container = ue.get_container(el)
    storey = ue.get_container(el, ifc_class="IfcBuildingStorey")
    parent = ue.get_aggregate(el)
    reps = el.Representation.Representations if el.Representation else ()
    return Element(
        global_id=el.GlobalId,
        step_id=el.id(),
        ifc_class=el.is_a(),
        name=el.Name,
        description=el.Description,
        object_type=el.ObjectType,
        predefined_type=ue.get_predefined_type(el),
        container_global_id=container.GlobalId if container else None,
        storey_global_id=storey.GlobalId if storey else None,
        parent_global_id=parent.GlobalId if parent else None,
        has_representation=bool(reps),
        representation_types=tuple(r.RepresentationType for r in reps if r.RepresentationType),
        properties=_properties(f, el),
        quantities=_quantities(f, el),
        materials=_materials(el),
        classifications=_classifications(el),
    )


def _properties(f: ifcopenshell.file, el: ifcopenshell.entity_instance) -> tuple[PropertyValue, ...]:
    out = []
    for pset_name, props in ue.get_psets(el, psets_only=True).items():
        units = _single_value_units(f, props.get("id"))
        out.extend(
            PropertyValue(pset=pset_name, name=k, value=_scalar(v), unit=units.get(k))
            for k, v in props.items()
            if k != "id"
        )
    return tuple(out)


def _single_value_units(f: ifcopenshell.file, pset_id: int | None) -> dict[str, str]:
    if pset_id is None:
        return {}
    pset = f.by_id(pset_id)
    props = pset.HasProperties if pset.is_a("IfcPropertySet") else ()
    return {
        p.Name: uu.get_full_unit_name(p.Unit)
        for p in props
        if p.is_a("IfcPropertySingleValue") and p.Unit and p.Unit.is_a("IfcNamedUnit")
    }


def _scalar(value: object) -> Scalar:
    """Lists/tables/complex values are stored as their string form; v1 rules only compare scalars."""
    return value if value is None or isinstance(value, str | int | float | bool) else str(value)


def _quantities(f: ifcopenshell.file, el: ifcopenshell.entity_instance) -> tuple[Quantity, ...]:
    out = []
    for qto_name, props in ue.get_psets(el, qtos_only=True).items():
        qto = f.by_id(props["id"])
        for q in qto.Quantities if qto.is_a("IfcElementQuantity") else ():
            if not q.is_a("IfcPhysicalSimpleQuantity") or q[3] is None:
                continue
            value = float(q[3])  # attribute 3 is the measure on every simple quantity
            unit = uu.get_property_unit(q, f)
            out.append(
                Quantity(
                    qto=qto_name,
                    name=q.Name,
                    value=value,
                    unit=uu.get_full_unit_name(unit) if unit else None,
                    si_value=value * uu.get_unit_scale(unit) if unit else value,
                )
            )
    return tuple(out)


def _materials(el: ifcopenshell.entity_instance) -> tuple[MaterialRef, ...]:
    top = ue.get_material(el, should_skip_usage=True)
    if top is None:
        return ()
    return tuple(MaterialRef(name=m.Name, kind=top.is_a()) for m in ue.get_materials(el) if m.Name)


def _classifications(el: ifcopenshell.entity_instance) -> tuple[ClassificationRef, ...]:
    refs = sorted(uc.get_references(el), key=lambda r: r.id())
    return tuple(_classification(r) for r in refs)


def _classification(ref: ifcopenshell.entity_instance) -> ClassificationRef:
    system = uc.get_classification(ref)
    ident = getattr(ref, "Identification", None) or getattr(ref, "ItemReference", None)
    return ClassificationRef(system=system.Name if system else None, identification=ident, name=ref.Name)
