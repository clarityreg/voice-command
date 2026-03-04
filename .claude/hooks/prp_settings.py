"""
Shared PRP settings loader for Python hooks.

Reads `.claude/prp-settings.json` and provides typed access to project
configuration. Falls back to sensible defaults when the file is missing.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULTS: Dict[str, Any] = {
    "project": {
        "name": "",
        "type": "",
        "backend_dir": "backend",
        "frontend_dir": "frontend",
    },
    "plane": {
        "workspace_slug": "",
        "project_id": "",
        "backlog_state_id": "",
        "api_url": "https://api.plane.so/api/v1",
    },
    "claude_secure_path": "",
    "coverage": {
        "targets": {"overall": 80, "critical": 90},
    },
    "ci": {
        "use_npm_ci": True,
        "node_version": "20",
        "python_version": "3.12",
    },
}


def _deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge *overlay* into *base*, returning a new dict."""
    result = dict(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def get_project_root() -> Path:
    """Return the project root directory."""
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(__file__).resolve().parents[2]


def load_settings(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """Load prp-settings.json, merged with defaults.

    Parameters
    ----------
    project_root : Path, optional
        Explicit project root.  Auto-detected when *None*.

    Returns
    -------
    dict
        Complete settings dict (defaults filled in for missing keys).
    """
    if project_root is None:
        project_root = get_project_root()

    settings_path = Path(project_root) / ".claude" / "prp-settings.json"
    if not settings_path.exists():
        return dict(DEFAULTS)

    try:
        with open(settings_path, "r", encoding="utf-8") as fh:
            user_settings = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)

    return _deep_merge(DEFAULTS, user_settings)


def _read_env_file(env_path: Path, key: str) -> Optional[str]:
    """Read a key from an env file without external dependencies.

    Supports ``KEY=value``, ``KEY="value"``, and ``KEY='value'`` formats.
    Lines starting with ``#`` are ignored.
    """
    if not env_path.exists():
        return None
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip()
            if k == key:
                # Strip surrounding quotes
                if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
                    v = v[1:-1]
                return v
    except OSError:
        pass
    return None


def get_plane_config(settings: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Extract Plane API config from settings + environment.

    The API key is resolved in order:
    1. ``PLANE_API_KEY`` environment variable
    2. ``.claude/prp-secrets.env`` file (PRP-specific secrets)

    The key is never stored in the settings JSON.

    Returns *None* when required fields are missing.
    """
    plane = settings.get("plane", {})
    workspace_slug = plane.get("workspace_slug", "")
    project_id = plane.get("project_id", "")
    api_url = plane.get("api_url", "https://api.plane.so/api/v1")

    if not workspace_slug or not project_id:
        return None

    # 1. Environment variable (highest priority)
    api_key = os.environ.get("PLANE_API_KEY")

    # 2. PRP-specific secrets file
    if not api_key:
        root = get_project_root()
        api_key = _read_env_file(root / ".claude" / "prp-secrets.env", "PLANE_API_KEY")

    if not api_key:
        return None

    return {
        "api_key": api_key,
        "api_url": api_url,
        "workspace_slug": workspace_slug,
        "project_id": project_id,
    }
