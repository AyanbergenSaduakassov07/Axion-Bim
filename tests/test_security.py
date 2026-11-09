"""Local-first hardening: DNS-rebinding Host check, cross-site write guard, IDS entity expansion."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from axiom.api import create_app
from axiom.config import Settings
from axiom.ids.adapter import load_ids

IDS = Path(__file__).parent.parent / "examples" / "ids" / "structural-basic.ids"
V1 = "/api/v1"
BOMB = '<?xml version="1.0"?>\n<!DOCTYPE ids [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;">]>\n'


@pytest.fixture
def client(tmp_path):
    settings = Settings(data_dir=tmp_path, db_url=f"sqlite:///{tmp_path / 'a.db'}")
    with TestClient(create_app(settings, run_jobs=False)) as c:
        yield c


def test_rejects_unknown_host_header(client):
    r = client.get(f"{V1}/projects", headers={"host": "evil.example"})
    assert r.status_code == 400


def test_accepts_localhost_host_with_port(client):
    assert client.get(f"{V1}/projects", headers={"host": "localhost:5173"}).status_code == 200


def test_rejects_cross_site_write(client):
    r = client.post(f"{V1}/projects", json={"name": "x"}, headers={"origin": "https://evil.example"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "cross_origin_write"


def test_allows_same_site_write_and_cross_site_read(client):
    local = {"origin": "http://localhost:5173"}
    assert client.post(f"{V1}/projects", json={"name": "x"}, headers=local).status_code == 201
    assert client.get(f"{V1}/projects", headers={"origin": "https://evil.example"}).status_code == 200


def test_load_ids_rejects_doctype(tmp_path):
    bomb = tmp_path / "bomb.ids"
    bomb.write_text(BOMB + IDS.read_text().split("?>", 1)[1])
    with pytest.raises(ValueError, match="DOCTYPE"):
        load_ids(bomb)


def test_ids_upload_with_doctype_is_400(client):
    body = BOMB + IDS.read_text().split("?>", 1)[1]
    r = client.post(f"{V1}/ids", files={"file": ("bomb.ids", body.encode(), "application/xml")})
    assert r.status_code == 400


@pytest.mark.parametrize("origin", ["null", "http://[bad", "https://localhost.evil.example"])
def test_rejects_malformed_or_lookalike_origin(client, origin):
    r = client.post(f"{V1}/projects", json={"name": "x"}, headers={"origin": origin})
    assert r.status_code == 403


def test_empty_allowed_hosts_env_falls_back_to_defaults(monkeypatch):
    from axiom.config import DEFAULT_HOSTS, load_settings  # noqa: PLC0415

    monkeypatch.setenv("AXIOM_ALLOWED_HOSTS", "")  # docker-compose passes ${VAR:-} as ""
    assert load_settings().allowed_hosts == DEFAULT_HOSTS
    monkeypatch.setenv("AXIOM_ALLOWED_HOSTS", "localhost, axiom.lan")
    assert load_settings().allowed_hosts == ("localhost", "axiom.lan")
