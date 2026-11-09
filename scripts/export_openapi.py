"""Write the API's OpenAPI schema to apps/web/src/api/openapi.json (consumed by P09).

Run: uv run python scripts/export_openapi.py
Then, in apps/web: npx openapi-typescript src/api/openapi.json -o src/api/schema.d.ts
"""

import json
import logging
from pathlib import Path

from axiom.api import create_app
from axiom.config import Settings

OUT = Path(__file__).resolve().parent.parent / "apps" / "web" / "src" / "api" / "openapi.json"


def main() -> None:
    # in-memory settings: building the schema needs no database or data dir
    app = create_app(Settings(data_dir=Path("unused"), db_url="sqlite://"), run_jobs=False)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")
    logging.basicConfig(level=logging.INFO)
    logging.getLogger(__name__).info("wrote %s", OUT)


if __name__ == "__main__":
    main()
