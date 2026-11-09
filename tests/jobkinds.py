"""Test-only job kinds, imported by spawned job children (D-18)."""

import os
import time


def echo(payload: dict, settings) -> dict:
    return {"echo": payload["x"]}


def sleep(payload: dict, settings) -> dict:
    time.sleep(payload["s"])
    return {}


def abort(payload: dict, settings) -> dict:
    os.abort()  # simulates a native crash (segfault in ifcopenshell)


def boom(payload: dict, settings) -> dict:
    raise RuntimeError("/secret/path/internal detail")


TEST_KINDS = {k: f"tests.jobkinds:{k}" for k in ("echo", "sleep", "abort", "boom")}
