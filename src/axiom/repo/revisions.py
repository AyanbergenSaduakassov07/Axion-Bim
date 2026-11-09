"""Revision persistence: Snapshot <-> rows. Callers (services) own the transaction."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import Connection, Row, func, insert, select

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
from axiom.repo.tables import (
    classifications,
    elements,
    material_assocs,
    property_values,
    quantities,
    revisions,
    spatial_nodes,
)

ORIGIN_COLS = ("origin_x", "origin_y", "origin_z")
CHILD_TABLES = (property_values, quantities, material_assocs, classifications)


def find_by_hash(conn: Connection, model_id: int, sha256: str) -> Row | None:
    q = select(revisions).where(revisions.c.model_id == model_id, revisions.c.file_sha256 == sha256)
    return conn.execute(q).first()


def insert_snapshot(conn: Connection, model_id: int, snap: Snapshot, status: str = "extracted") -> Row:
    seq = conn.execute(
        select(func.coalesce(func.max(revisions.c.seq), 0) + 1).where(revisions.c.model_id == model_id)
    ).scalar_one()
    meta = snap.meta
    rev = conn.execute(
        insert(revisions).returning(revisions),
        {
            "model_id": model_id,
            "seq": seq,
            "file_sha256": meta.file_sha256,
            "file_size": meta.file_size,
            "schema_name": meta.schema_name,
            "length_scale": meta.length_scale,
            "status": status,
            "metadata_json": meta.model_dump(mode="json"),
        },
    ).one()
    if snap.spatial:
        conn.execute(insert(spatial_nodes), [{"revision_id": rev.id, **n.model_dump()} for n in snap.spatial])
    if snap.elements:
        _insert_elements(conn, rev.id, snap.elements)
    return rev


def _insert_elements(conn: Connection, revision_id: int, els: tuple[Element, ...]) -> None:
    ids = (
        conn.execute(
            insert(elements).returning(elements.c.id, sort_by_parameter_order=True),
            [_element_row(revision_id, e) for e in els],
        )
        .scalars()
        .all()
    )
    rows: dict[str, list[dict]] = defaultdict(list)
    for el_id, e in zip(ids, els, strict=True):
        rows["property_values"] += [{"element_id": el_id, **_encode_property(p)} for p in e.properties]
        rows["quantities"] += [{"element_id": el_id, **q.model_dump()} for q in e.quantities]
        rows["material_assocs"] += [{"element_id": el_id, **m.model_dump()} for m in e.materials]
        rows["classifications"] += [{"element_id": el_id, **c.model_dump()} for c in e.classifications]
    for table in CHILD_TABLES:
        if rows[table.name]:
            conn.execute(insert(table), rows[table.name])


def _element_row(revision_id: int, e: Element) -> dict:
    return {
        "revision_id": revision_id,
        "global_id": e.global_id,
        "step_id": e.step_id,
        "ifc_class": e.ifc_class,
        "name": e.name,
        "description": e.description,
        "object_type": e.object_type,
        "predefined_type": e.predefined_type,
        "container_global_id": e.container_global_id,
        "storey_global_id": e.storey_global_id,
        "parent_global_id": e.parent_global_id,
        "has_geometry": e.has_representation,
        "representation_types": ",".join(e.representation_types),
        **dict(zip(ORIGIN_COLS, e.origin_m or (None, None, None), strict=True)),
    }


def _encode_property(p: PropertyValue) -> dict:
    v = p.value
    kind = "null" if v is None else type(v).__name__
    num = float(v) if isinstance(v, int | float) else None  # bool is an int subclass
    return {
        "pset": p.pset,
        "name": p.name,
        "unit": p.unit,
        "value_type": kind,
        "value_num": num,
        "value_text": v if isinstance(v, str) else None,
    }


def _decode_value(row: Row) -> Scalar:
    return {
        "null": lambda: None,
        "str": lambda: row.value_text,
        "bool": lambda: bool(row.value_num),
        "int": lambda: int(row.value_num),
        "float": lambda: row.value_num,
    }[row.value_type]()


def load_snapshot(conn: Connection, revision_id: int) -> Snapshot:
    rev = conn.execute(select(revisions).where(revisions.c.id == revision_id)).one()
    spatial = conn.execute(
        select(spatial_nodes).where(spatial_nodes.c.revision_id == revision_id).order_by(spatial_nodes.c.id)
    ).all()
    el_rows = conn.execute(
        select(elements).where(elements.c.revision_id == revision_id).order_by(elements.c.id)
    ).all()
    children = {t.name: _children(conn, t, elements.c.revision_id == revision_id) for t in CHILD_TABLES}
    return Snapshot(
        meta=RevisionMeta.model_validate(rev.metadata_json),
        spatial=tuple(SpatialNode(**_fields(r, SpatialNode)) for r in spatial),
        elements=tuple(_element(r, children) for r in el_rows),
    )


def load_element(conn: Connection, revision_id: int, global_id: str) -> Element | None:
    q = select(elements).where(elements.c.revision_id == revision_id, elements.c.global_id == global_id)
    r = conn.execute(q.order_by(elements.c.id).limit(1)).first()
    if r is None:
        return None
    return _element(r, {t.name: _children(conn, t, elements.c.id == r.id) for t in CHILD_TABLES})


def _children(conn: Connection, table, where) -> dict[int, list[Row]]:
    q = select(table).join(elements, table.c.element_id == elements.c.id).where(where).order_by(table.c.id)
    out: dict[int, list[Row]] = defaultdict(list)
    for r in conn.execute(q):
        out[r.element_id].append(r)
    return out


def _fields(row: Row, model: type) -> dict:
    return {k: getattr(row, k) for k in model.model_fields}


def _element(r: Row, children: dict[str, dict[int, list[Row]]]) -> Element:
    return Element(
        **{
            k: getattr(r, k)
            for k in Element.model_fields
            if k in r._fields and k not in ("representation_types",)
        },
        has_representation=r.has_geometry,
        representation_types=tuple(t for t in r.representation_types.split(",") if t),
        origin_m=(r.origin_x, r.origin_y, r.origin_z) if r.origin_x is not None else None,
        properties=tuple(
            PropertyValue(pset=p.pset, name=p.name, value=_decode_value(p), unit=p.unit)
            for p in children["property_values"][r.id]
        ),
        quantities=tuple(Quantity(**_fields(q, Quantity)) for q in children["quantities"][r.id]),
        materials=tuple(MaterialRef(**_fields(m, MaterialRef)) for m in children["material_assocs"][r.id]),
        classifications=tuple(
            ClassificationRef(**_fields(c, ClassificationRef)) for c in children["classifications"][r.id]
        ),
    )


def revision_seq(conn: Connection, revision_id: int) -> int:
    return conn.execute(select(revisions.c.seq).where(revisions.c.id == revision_id)).scalar_one()
