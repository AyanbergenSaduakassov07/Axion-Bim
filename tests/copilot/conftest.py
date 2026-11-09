from dataclasses import dataclass

import pytest

from axiom.copilot.eval import SeededProject, seed_project
from axiom.repo.db import get_engine, migrate


@dataclass(frozen=True)
class Seeded:
    engine: object
    project: SeededProject


@pytest.fixture(scope="session")
def seeded(tmp_path_factory, ifc_path) -> Seeded:
    """rev1..rev3 of model "Structure" (+ IDS) and the injection fixture as model "Injection"."""
    root = tmp_path_factory.mktemp("copilot")
    engine = get_engine(f"sqlite:///{root / 'c.db'}")
    migrate(engine)
    return Seeded(engine, seed_project(engine, root / "files", ifc_path))
