"""Frozen acceptance certificates: insert and read only."""

from __future__ import annotations

from sqlalchemy import Connection, Row, insert, select

from axiom.repo.tables import certificates

COLUMNS = (certificates.c.id, certificates.c.payload_json, certificates.c.sha256, certificates.c.created_at)


def insert_certificate(conn: Connection, audit_run_id: int, payload: dict, sha256: str) -> int:
    row = {"audit_run_id": audit_run_id, "payload_json": payload, "sha256": sha256}
    return conn.execute(insert(certificates).returning(certificates.c.id), row).scalar_one()


def list_for_audit(conn: Connection, audit_run_id: int) -> list[Row]:
    q = select(*COLUMNS).where(certificates.c.audit_run_id == audit_run_id).order_by(certificates.c.id)
    return list(conn.execute(q))
