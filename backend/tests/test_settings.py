"""Tests for settings API endpoints."""

import json
from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def settings_file(tmp_path, monkeypatch):
    """Point settings manager at a temporary file."""
    import clarity_backend.settings.manager as mgr

    settings_dir = tmp_path / ".clarity"
    settings_file = settings_dir / "settings.json"
    monkeypatch.setattr(mgr, "SETTINGS_DIR", settings_dir)
    monkeypatch.setattr(mgr, "SETTINGS_FILE", settings_file)
    return settings_file


@pytest.mark.asyncio
async def test_get_settings_defaults(client: AsyncClient):
    """Returns default settings when no file exists."""
    resp = await client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plane_api_key"] == ""
    assert data["focus_minutes"] == 25
    assert data["break_minutes"] == 5


@pytest.mark.asyncio
async def test_put_settings_saves(client: AsyncClient, settings_file: Path):
    """PUT updates settings and returns masked secrets."""
    resp = await client.put(
        "/api/settings",
        json={"plane_api_key": "sk-test-12345678", "focus_minutes": 30},
    )
    assert resp.status_code == 200
    data = resp.json()
    # API key is masked in response
    assert data["plane_api_key"].startswith("sk-t")
    assert "*" in data["plane_api_key"]
    assert data["focus_minutes"] == 30

    # File was written
    raw = json.loads(settings_file.read_text())
    assert raw["plane_api_key"] == "sk-test-12345678"
    assert raw["focus_minutes"] == 30


@pytest.mark.asyncio
async def test_put_settings_ignores_masked_values(client: AsyncClient, settings_file: Path):
    """PUT with masked secret values does not overwrite real secrets."""
    # First write a real key
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(json.dumps({"plane_api_key": "sk-real-secret"}))

    # Now send a masked value back — should be ignored
    resp = await client.put(
        "/api/settings",
        json={"plane_api_key": "sk-r**********", "focus_minutes": 15},
    )
    assert resp.status_code == 200

    raw = json.loads(settings_file.read_text())
    assert raw["plane_api_key"] == "sk-real-secret"
    assert raw["focus_minutes"] == 15


@pytest.mark.asyncio
async def test_get_settings_reads_file(client: AsyncClient, settings_file: Path):
    """GET reads from the settings file."""
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(json.dumps({"plane_workspace_slug": "my-workspace"}))

    resp = await client.get("/api/settings")
    assert resp.json()["plane_workspace_slug"] == "my-workspace"


@pytest.mark.asyncio
async def test_get_settings_masks_secrets(client: AsyncClient, settings_file: Path):
    """Secrets are masked in GET response."""
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(json.dumps({
        "plane_api_key": "sk-abcdef123456",
        "aikido_webhook_secret": "whsec_longvalue",
    }))

    resp = await client.get("/api/settings")
    data = resp.json()
    # "sk-abcdef123456" = 15 chars, first 4 shown + 11 asterisks
    assert data["plane_api_key"] == "sk-a" + "*" * 11
    # "whsec_longvalue" = 15 chars, first 4 shown + 11 asterisks
    assert data["aikido_webhook_secret"] == "whse" + "*" * 11
