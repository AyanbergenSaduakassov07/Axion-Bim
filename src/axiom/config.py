"""Runtime settings from environment. No secrets here; the copilot key is read where it is used."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_HOSTS = ("localhost", "127.0.0.1", "::1", "testserver")  # testserver = Starlette TestClient


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    db_url: str
    max_upload_mb: int = 500
    job_timeout_s: float = 900.0
    job_mem_mb: int = 8192
    allowed_hosts: tuple[str, ...] = DEFAULT_HOSTS

    @property
    def files_dir(self) -> Path:
        return self.data_dir / "files"


def load_settings() -> Settings:
    data_dir = Path(os.environ.get("AXIOM_DATA_DIR", "data"))
    hosts = os.environ.get("AXIOM_ALLOWED_HOSTS", "").strip()  # "" from docker-compose = default
    return Settings(
        data_dir=data_dir,
        db_url=os.environ.get("AXIOM_DB_URL", f"sqlite:///{data_dir / 'axiom.db'}"),
        max_upload_mb=int(os.environ.get("AXIOM_MAX_UPLOAD_MB", "500")),
        job_timeout_s=float(os.environ.get("AXIOM_JOB_TIMEOUT_S", "900")),
        job_mem_mb=int(os.environ.get("AXIOM_JOB_MEM_MB", "8192")),
        allowed_hosts=tuple(h.strip() for h in hosts.split(",")) if hosts else DEFAULT_HOSTS,
    )
