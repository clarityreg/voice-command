"""Settings manager — read/write JSON settings from ~/.clarity/settings.json."""

import json
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/settings", tags=["settings"])

SETTINGS_DIR = Path.home() / ".clarity"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

# Keys whose values are masked in GET responses
SECRET_KEYS = {
    "plane_api_key",
    "aikido_webhook_secret",
    "openai_api_key",
    "posthog_api_key",
    "clarity_api_key",
    "clarity_webhook_secret",
}

DEFAULT_SETTINGS: dict = {
    "plane_api_key": "",
    "plane_workspace_slug": "",
    "plane_project_id": "",
    "plane_projects": {},  # { alias: { id, name, identifier } }
    "plane_done_state_name": "Done",
    "openai_api_key": "",
    "stt_backend": "web-speech",  # "web-speech" | "whisper" | "openai-whisper"
    "aikido_webhook_secret": "",
    "posthog_api_key": "",
    "posthog_project_id": "",
    "posthog_host": "https://eu.posthog.com",
    "focus_minutes": 25,
    "break_minutes": 5,
    "clarity_api_url": "http://localhost:8000",
    "clarity_api_key": "",
    "clarity_webhook_secret": "",
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
    openai_api_key: str | None = None
    stt_backend: str | None = None
    aikido_webhook_secret: str | None = None
    posthog_api_key: str | None = None
    posthog_project_id: str | None = None
    posthog_host: str | None = None
    focus_minutes: int | None = None
    break_minutes: int | None = None
    clarity_api_url: str | None = None
    clarity_api_key: str | None = None
    clarity_webhook_secret: str | None = None


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


@router.post("/plane/sync-projects")
async def sync_plane_projects() -> dict:
    """Fetch all projects from Plane, merge into settings preserving existing aliases."""
    from clarity_backend.config import settings as env_settings
    from clarity_backend.integrations.plane import PlaneClient

    current = _read_settings()
    api_key = current.get("plane_api_key") or env_settings.PLANE_API_KEY
    workspace = current.get("plane_workspace_slug") or env_settings.PLANE_WORKSPACE_SLUG
    base_url = env_settings.PLANE_API_URL

    if not api_key or not workspace:
        return {"error": "Plane API key and workspace slug are required.", "projects": {}}

    client = PlaneClient(api_key=api_key, workspace_slug=workspace, base_url=base_url)
    try:
        raw_projects = await client.list_projects()
    except Exception as e:
        return {"error": f"Failed to fetch projects: {e}", "projects": {}}

    existing: dict = current.get("plane_projects", {})

    # Build reverse lookup: project_id -> alias
    id_to_alias = {v["id"]: k for k, v in existing.items() if "id" in v}

    for proj in raw_projects:
        pid = str(proj.get("id", ""))
        name = proj.get("name", "Untitled")
        identifier = proj.get("identifier", "")

        if pid in id_to_alias:
            # Preserve existing alias, update name/identifier
            alias = id_to_alias[pid]
            existing[alias]["name"] = name
            existing[alias]["identifier"] = identifier
        else:
            # Auto-generate alias: lowercase first word of name
            alias = name.split()[0].lower() if name else pid[:8]
            # Avoid collisions
            base_alias = alias
            counter = 2
            while alias in existing:
                alias = f"{base_alias}{counter}"
                counter += 1
            existing[alias] = {"id": pid, "name": name, "identifier": identifier}

    current["plane_projects"] = existing
    _write_settings(current)
    return {"projects": existing}


@router.put("/plane/projects/{alias}")
async def update_project_alias(alias: str, body: dict) -> dict:
    """Add or update a custom alias for a Plane project."""
    current = _read_settings()
    projects = current.get("plane_projects", {})

    new_alias = body.get("new_alias", "").strip().lower()
    if not new_alias:
        return {"error": "Alias cannot be empty."}

    if new_alias in projects and new_alias != alias:
        return {"error": f"Alias '{new_alias}' already exists."}

    if alias in projects:
        # Rename alias
        entry = projects.pop(alias)
        projects[new_alias] = entry
    elif "id" in body:
        # Create new alias pointing to a project ID
        projects[new_alias] = {
            "id": body["id"],
            "name": body.get("name", new_alias),
            "identifier": body.get("identifier", ""),
        }
    else:
        return {"error": f"Project alias '{alias}' not found."}

    current["plane_projects"] = projects
    _write_settings(current)
    return {"projects": projects}


@router.delete("/plane/projects/{alias}")
async def delete_project_alias(alias: str) -> dict:
    """Remove a project alias."""
    current = _read_settings()
    projects = current.get("plane_projects", {})
    if alias in projects:
        del projects[alias]
        current["plane_projects"] = projects
        _write_settings(current)
    return {"projects": projects}


def get_plane_projects() -> dict[str, dict]:
    """Return the plane_projects registry from settings."""
    return _read_settings().get("plane_projects", {})
