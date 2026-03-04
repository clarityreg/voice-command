"""
Constants for Observability Hooks.
"""

import os
from pathlib import Path

# Base directory for all logs — defaults to observability logs dir within hooks
LOG_BASE_DIR = os.environ.get(
    "CLAUDE_HOOKS_LOG_DIR",
    os.path.join(os.path.dirname(__file__), "logs")
)


def get_session_log_dir(session_id: str) -> Path:
    """
    Get the log directory for a specific session.

    Args:
        session_id: The Claude session ID

    Returns:
        Path object for the session's log directory
    """
    return Path(LOG_BASE_DIR) / session_id


def ensure_session_log_dir(session_id: str) -> Path:
    """
    Ensure the log directory for a session exists.

    Args:
        session_id: The Claude session ID

    Returns:
        Path object for the session's log directory
    """
    log_dir = get_session_log_dir(session_id)
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir
