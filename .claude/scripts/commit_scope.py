#!/usr/bin/env python3
"""
Commit Scope Analyser Hook
---------------------------
Fires before any `git commit` command.
Checks staged files to detect if they span unrelated areas of the codebase.
Warns (non-blocking) when commits look like they contain mixed concerns.

Think of it like a mirror: it shows you what you're actually committing
vs what you think you're committing.
"""
import json
import sys
import re
import subprocess
import os
from collections import defaultdict

data = json.load(sys.stdin)
command = data.get("tool_input", {}).get("command", "")

# Only fire on git commit
if not re.search(r"\bgit\s+commit\b", command):
    sys.exit(0)

try:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        timeout=5
    )
    staged_files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
except Exception:
    sys.exit(0)

if len(staged_files) == 0:
    sys.exit(0)

# Categorise files by domain area
DOMAIN_RULES = {
    "backend": lambda f: any(f.startswith(p) for p in ["backend/", "api/", "services/", "apps/"]) or f.endswith(".py"),
    "frontend": lambda f: any(f.startswith(p) for p in ["frontend/", "src/components", "src/pages", "src/app"]) or f.endswith((".tsx", ".ts", ".jsx", ".js", ".css")),
    "database": lambda f: any(p in f for p in ["/migrations/", "supabase/", "schema.", "seed."]),
    "infrastructure": lambda f: any(f.startswith(p) for p in ["docker", "infra/", ".github/", "nginx/", "traefik/"]) or f.endswith((".yml", ".yaml", "Dockerfile")),
    "config": lambda f: any(f in [".env.example", "settings.py", "pyproject.toml", "package.json", "requirements.txt"]),
    "docs": lambda f: f.endswith(".md") or f.startswith("docs/"),
}

domains_touched = defaultdict(list)
for f in staged_files:
    matched = False
    for domain, rule in DOMAIN_RULES.items():
        if rule(f):
            domains_touched[domain].append(f)
            matched = True
            break
    if not matched:
        domains_touched["other"].append(f)

# Ignore docs + one other domain (that's usually fine)
significant_domains = {k: v for k, v in domains_touched.items() if k != "docs"}

if len(significant_domains) >= 3:
    domain_summary = "\n".join(
        f"  [{domain.upper()}] {', '.join(files[:3])}{'...' if len(files) > 3 else ''}"
        for domain, files in significant_domains.items()
    )
    # Non-blocking — print warning to stderr, Claude will see it
    warning = (
        f"\n⚠️  SCOPE WARNING: This commit touches {len(significant_domains)} different areas:\n"
        f"{domain_summary}\n\n"
        "This looks like a mixed-concern commit. Consider:\n"
        "  1. Staging only related files with: git add <specific-files>\n"
        "  2. Splitting into multiple focused commits\n"
        "  3. Confirming this is intentional before proceeding\n"
        "\nTotal staged files: " + str(len(staged_files))
    )
    print(warning, file=sys.stderr)
    # Exit 1 = non-blocking warning (Claude sees it but isn't blocked)
    sys.exit(1)

sys.exit(0)
