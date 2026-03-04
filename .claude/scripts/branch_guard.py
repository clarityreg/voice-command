#!/usr/bin/env python3
"""
Branch Guard Hook
-----------------
Fires on any Bash command or file edit.
Blocks Claude from making changes when on main or develop.
Forces the user to create a feature branch first.
"""
import json
import sys
import subprocess

data = json.load(sys.stdin)

# Allow branch creation commands — that's how you leave a protected branch
command = data.get("tool_input", {}).get("command", "")
import re
if re.search(r"git\s+(checkout\s+-b|switch\s+-c|branch\s+\S)", command):
    sys.exit(0)

try:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        timeout=5
    )
    branch = result.stdout.strip()
except Exception:
    sys.exit(0)  # Can't determine branch, allow through

PROTECTED_BRANCHES = ("main", "master", "develop", "dev")

if branch in PROTECTED_BRANCHES:
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"⛔ BRANCH GUARD: You are on '{branch}' — a protected branch.\n\n"
            "You must create a feature branch before making changes.\n\n"
            "Use one of these conventions:\n"
            "  git checkout -b feature/describe-your-feature\n"
            "  git checkout -b fix/describe-the-bug\n"
            "  git checkout -b hotfix/critical-issue\n"
            "  git checkout -b chore/task-description\n"
            "  git checkout -b docs/what-you-are-documenting\n\n"
            "Ask yourself: can I describe this change in ONE sentence?\n"
            "If yes — name your branch after that sentence."
        )
    }))

sys.exit(0)
