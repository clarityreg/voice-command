#!/usr/bin/env python3
"""
Status Line
============
Configured via settings.json "statusLine" (not a hook event).
Merges context window data (from stdin JSON) with git info.

Output: [Model] [###------] 25.0% | feature/my-branch | 2 dirty | 14:32
"""
import json
import subprocess
import sys
from datetime import datetime

# ANSI color codes
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
DIM = "\033[90m"
RESET = "\033[0m"


def get_branch() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=3,
        )
        return r.stdout.strip() if r.returncode == 0 else "?"
    except Exception:
        return "?"


def get_dirty_count() -> int:
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=3,
        )
        if r.returncode != 0:
            return 0
        return len([line for line in r.stdout.strip().splitlines() if line.strip()])
    except Exception:
        return 0


def get_usage_color(percentage):
    """Get color based on context window usage percentage."""
    if percentage < 50:
        return GREEN
    elif percentage < 75:
        return YELLOW
    elif percentage < 90:
        return RED
    else:
        return "\033[91m"  # Bright red for critical


def create_progress_bar(percentage, width=9):
    """Create a visual progress bar."""
    filled = int((percentage / 100) * width)
    empty = width - filled

    color = get_usage_color(percentage)
    bar = f"{color}{'#' * filled}{DIM}{'-' * empty}{RESET}"
    return f"[{bar}]"


def format_tokens(tokens):
    """Format token count in human-readable format."""
    if tokens is None or tokens < 0:
        return "0"
    if tokens < 1000:
        return str(int(tokens))
    elif tokens < 1000000:
        return f"{tokens / 1000:.0f}k"
    else:
        return f"{tokens / 1000000:.1f}M"


def main():
    # Try to read context window data from stdin
    input_data = {}
    try:
        raw = sys.stdin.read()
        if raw.strip():
            input_data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        pass

    # Extract model and context window info
    model_info = input_data.get("model", {})
    model_name = model_info.get("display_name", "")

    context_data = input_data.get("context_window", {})
    used_percentage = context_data.get("used_percentage", 0) or 0
    context_window_size = context_data.get("context_window_size", 0) or 0

    # Git info
    branch = get_branch()
    dirty = get_dirty_count()
    now = datetime.now().strftime("%H:%M")

    parts = []

    # Context window section (only if data is available)
    if model_name:
        parts.append(f"{CYAN}[{model_name}]{RESET}")

    if context_window_size > 0:
        usage_color = get_usage_color(used_percentage)
        progress_bar = create_progress_bar(used_percentage)
        parts.append(f"{progress_bar} {usage_color}{used_percentage:.1f}%{RESET}")

    # Git section
    parts.append(branch)
    if dirty > 0:
        parts.append(f"{dirty} dirty")
    parts.append(now)

    print(" | ".join(parts))


if __name__ == "__main__":
    main()
