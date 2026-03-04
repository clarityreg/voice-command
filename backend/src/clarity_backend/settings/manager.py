"""Settings manager — read/write JSON settings from ~/.clarity/settings.json."""

import json
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/settings", tags=["settings"])

SETTINGS_DIR = Path.home() / ".clarity"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

# Keys whose values are masked in GET responses
SECRET_KEYS = {"plane_api_key", "aikido_webhook_secret"}

DEFAULT_SETTINGS: dict = {
    "plane_api_key": "",
    "plane_workspace_slug": "",
    "plane_project_id": "",
    "aikido_webhook_secret": "",
    "focus_minutes": 25,
    "break_minutes": 5,
}


def _read_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return dict(DEFAULT_SETTINGS)
    try:
        data = json.loads(SETTINGS_FILE.read_text())
        merged = dict(DEFAULT_SETTINGS)
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_SETTINGS)


def _write_settings(data: dict) -> None:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, indent=2) + "\n")


def _mask(settings: dict) -> dict:
    masked = dict(settings)
    for key in SECRET_KEYS:
        val = masked.get(key, "")
        if val:
            masked[key] = val[:4] + "*" * max(0, len(val) - 4)
    return masked


class SettingsUpdate(BaseModel):
    plane_api_key: str | None = None
    plane_workspace_slug: str | None = None
    plane_project_id: str | None = None
    aikido_webhook_secret: str | None = None
    focus_minutes: int | None = None
    break_minutes: int | None = None


@router.get("")
async def get_settings() -> dict:
    return _mask(_read_settings())


@router.put("")
async def update_settings(body: SettingsUpdate) -> dict:
    current = _read_settings()
    updates = body.model_dump(exclude_none=True)
    # Don't overwrite secrets with masked values
    for key in SECRET_KEYS:
        if key in updates and "*" in updates[key]:
            del updates[key]
    current.update(updates)
    _write_settings(current)
    return _mask(current)
