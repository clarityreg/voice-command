#!/usr/bin/env python3
"""
Session Start Context Injector
--------------------------------
Fires when Claude Code starts a session.
Injects current git state into Claude's system prompt so it's
immediately aware of where you are before any work begins.

Like a morning briefing before a workday — you know what's in progress
before you pick up a tool.
"""
import json
import sys
import subprocess
from datetime import datetime

def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""

branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
dirty = run(["git", "status", "--short"])
recent_commits = run(["git", "log", "--oneline", "-5"])
stash_list = run(["git", "stash", "list"])
open_branches = run(["git", "branch", "--sort=-committerdate", "--format=%(refname:short) (%(committerdate:relative))", "-10"])

PROTECTED_BRANCHES = ("main", "master", "develop", "dev")

branch_warning = ""
if branch in PROTECTED_BRANCHES:
    branch_warning = (
        f"\n⚠️  WARNING: You are on '{branch}' — a PROTECTED branch. "
        "Create a feature branch before making any changes.\n"
    )

context_parts = [
    f"=== GIT CONTEXT (session started {datetime.now().strftime('%H:%M')}) ===",
    f"Current branch: {branch}{' ⚠️ PROTECTED' if branch in PROTECTED_BRANCHES else ''}",
    branch_warning,
]

if dirty:
    context_parts.append(f"\nUncommitted changes:\n{dirty}")
else:
    context_parts.append("\nWorking tree: clean")

if recent_commits:
    context_parts.append(f"\nRecent commits on this branch:\n{recent_commits}")

if stash_list:
    context_parts.append(f"\nStashed work:\n{stash_list}")

if open_branches:
    context_parts.append(f"\nRecent local branches:\n{open_branches}")

context_parts.append(
    "\n=== WORKFLOW REMINDER ===\n"
    "One branch = one job. If you notice something else that needs fixing,\n"
    "write it down as a GitHub issue — don't fix it here."
)

context = "\n".join(context_parts)

print(json.dumps({"additionalContext": context}))
sys.exit(0)
