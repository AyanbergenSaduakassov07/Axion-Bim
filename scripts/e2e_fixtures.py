"""Build the IFC fixtures the web smoke test uploads: `python scripts/e2e_fixtures.py OUT_DIR`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tests" / "fixtures"))
from factory import build_fixture  # noqa: E402

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
for name in ("rev1", "rev2", "rev3"):
    build_fixture(name, out)
