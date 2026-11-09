"""Snapshot: the normalized, immutable view of one IFC revision. Everything downstream reads this, not IFC."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

Scalar = str | int | float | bool | None


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PropertyValue(Frozen):
    pset: str
    name: str
    value: Scalar
    unit: str | None = None


class Quantity(Frozen):
    qto: str
    name: str
    value: float
    unit: str | None  # raw unit name as declared in the file, e.g. MILLIMETRE
    si_value: float
    method: str = "qto"  # qto | geometry


class MaterialRef(Frozen):
    name: str
    kind: str  # top-level material definition class: IfcMaterial, IfcMaterialLayerSet, ...


class ClassificationRef(Frozen):
    system: str | None
    identification: str | None
    name: str | None


class Element(Frozen):
    global_id: str
    step_id: int  # == viewer localId (D-11); disambiguates duplicate GlobalIds
    ifc_class: str
    name: str | None
    description: str | None
    object_type: str | None
    predefined_type: str | None
    container_global_id: str | None
    storey_global_id: str | None
    parent_global_id: str | None  # aggregate parent
    has_representation: bool
    representation_types: tuple[str, ...]
    properties: tuple[PropertyValue, ...]
    quantities: tuple[Quantity, ...]
    materials: tuple[MaterialRef, ...]
    classifications: tuple[ClassificationRef, ...]
    origin_m: tuple[float, float, float] | None = None  # world placement origin; old snapshots lack it


class SpatialNode(Frozen):
    global_id: str
    ifc_class: str
    name: str | None
    parent_global_id: str | None
    elevation_m: float | None


class RevisionMeta(Frozen):
    schema_name: str
    length_scale: float  # file length unit -> metres
    units: dict[str, str]  # unit type -> full unit name
    authoring_app: str | None
    project_name: str | None
    georef: dict[str, Scalar] | None
    file_sha256: str
    file_size: int


class Snapshot(Frozen):
    meta: RevisionMeta
    spatial: tuple[SpatialNode, ...]
    elements: tuple[Element, ...]
