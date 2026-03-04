#!/usr/bin/env python3
"""
Branch Naming Enforcer Hook
----------------------------
Intercepts `git checkout -b` commands.
Blocks branch creation if the name doesn't match convention.
"""
import json
import sys
import re

data = json.load(sys.stdin)
command = data.get("tool_input", {}).get("command", "")

# Only care about branch creation commands
if not re.search(r"git\s+checkout\s+-b\s+", command) and not re.search(r"git\s+switch\s+-c\s+", command):
    sys.exit(0)

# Extract the branch name
match = re.search(r"git\s+(?:checkout\s+-b|switch\s+-c)\s+([\w/._-]+)", command)
if not match:
    sys.exit(0)

branch_name = match.group(1)

VALID_PREFIXES = [
    "feature/",
    "fix/",
    "hotfix/",
    "chore/",
    "docs/",
    "refactor/",
    "test/",
    "release/",
]

VALID_PATTERN = re.compile(r"^(feature|fix|hotfix|chore|docs|refactor|test|release)/[a-z0-9][a-z0-9-]+$")

if not VALID_PATTERN.match(branch_name):
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"⛔ BRANCH NAMING: '{branch_name}' does not follow the naming convention.\n\n"
            "Branch names must use one of these prefixes:\n"
            "  feature/   → new functionality\n"
            "  fix/       → bug fixes\n"
            "  hotfix/    → critical production fixes\n"
            "  chore/     → maintenance, dependencies, config\n"
            "  docs/      → documentation only\n"
            "  refactor/  → code restructuring, no behaviour change\n"
            "  test/      → adding or fixing tests\n"
            "  release/   → release preparation\n\n"
            "Examples:\n"
            "  feature/ingredient-search\n"
            "  fix/login-redirect-loop\n"
            "  chore/update-dependencies\n\n"
            "Use lowercase letters, numbers, and hyphens only."
        )
    }))

sys.exit(0)
