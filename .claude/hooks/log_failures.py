#!/usr/bin/env python3
"""
Tool Failure Logger (PostToolUseFailure)
========================================
Appends a JSON line to tool_failures.jsonl with timestamp, tool name,
truncated input, error message, and git branch. Plays error sound.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path(__file__).parent / "tool_failures.jsonl"
ERROR_SOUND = Path(__file__).parent / "sounds" / "voice" / "error.aiff"
MAX_INPUT_LEN = 500


def get_git_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=3,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def truncate(value, max_len: int) -> str:
    s = json.dumps(value) if not isinstance(value, str) else value
    return s[:max_len] + "..." if len(s) > max_len else s


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool_name": data.get("tool_name", ""),
        "tool_input": truncate(data.get("tool_input", {}), MAX_INPUT_LEN),
        "error": truncate(data.get("tool_result", data.get("error", "")), MAX_INPUT_LEN),
        "branch": get_git_branch(),
    }

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Best-effort logging

    # Play error sound (non-blocking)
    if ERROR_SOUND.exists():
        try:
            subprocess.Popen(
                ["afplay", "-v", "0.2", str(ERROR_SOUND)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    sys.exit(0)


if __name__ == "__main__":
    main()
