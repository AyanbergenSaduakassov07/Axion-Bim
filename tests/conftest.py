from pathlib import Path

import pytest
import yaml

from tests.fixtures.factory import build_fixture

EXPECTED_DIR = Path(__file__).parent / "fixtures" / "expected"


@pytest.fixture(scope="session")
def fixture_dir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("ifc")


@pytest.fixture(scope="session")
def ifc_path(fixture_dir):
    """Return a builder: ifc_path("clean") -> Path to the generated IFC (built once per session)."""
    cache: dict[str, Path] = {}

    def _get(name: str) -> Path:
        if name not in cache:
            cache[name] = build_fixture(name, fixture_dir)
        return cache[name]

    return _get


def load_expected(name: str) -> dict:
    return yaml.safe_load((EXPECTED_DIR / f"{name}.yaml").read_text())
