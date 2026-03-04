#!/usr/bin/env python3
"""
branch_viz_refresh.py — PostToolUse hook that regenerates branch-viz.html
after git operations that change branch state (commit, push, merge, checkout -b, branch).

Runs the regeneration in background so it doesn't block the user.
"""

import json
import os
import re
import subprocess
import sys

GIT_TRIGGERS = re.compile(
    r"\bgit\s+(commit|push|merge|checkout\s+-b|branch\s+\S|rebase|pull)\b"
)


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        return

    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        return

    # Only trigger on Bash tool completions
    tool_name = event.get("tool_name", "")
    if tool_name != "Bash":
        return

    # Check if the command was a git operation that changes branch state
    tool_input = event.get("tool_input", {})
    command = tool_input.get("command", "")
    if not GIT_TRIGGERS.search(command):
        return

    # Only regenerate if the script exists
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return

    script = os.path.join(project_dir, "scripts", "branch-viz.py")
    if not os.path.exists(script):
        return

    # Run in background — don't block the user
    try:
        subprocess.Popen(
            ["python3", script],
            cwd=project_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass  # Best-effort


if __name__ == "__main__":
    main()
