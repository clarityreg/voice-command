#!/usr/bin/env python3
"""
Pre-Push PR Checklist Hook
---------------------------
Fires before any `git push` command.
Runs a checklist and injects it into Claude's context as a reminder.
Non-blocking — designed as a forcing function to pause and reflect,
not to stop legitimate work.

Think of it like a pilot's pre-flight checklist: you don't take off
without running through it, even if you've done it a thousand times.
"""
import json
import sys
import re
import subprocess

data = json.load(sys.stdin)
command = data.get("tool_input", {}).get("command", "")

# Only fire on git push
if not re.search(r"\bgit\s+push\b", command):
    sys.exit(0)

# Get current branch
try:
    branch_result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, timeout=5
    )
    branch = branch_result.stdout.strip()

    # Get commit count ahead of remote
    log_result = subprocess.run(
        ["git", "log", "--oneline", f"origin/{branch}..HEAD"],
        capture_output=True, text=True, timeout=5
    )
    commits = [l for l in log_result.stdout.splitlines() if l.strip()]

    # Get changed files vs remote
    diff_result = subprocess.run(
        ["git", "diff", "--name-only", f"origin/{branch}...HEAD"],
        capture_output=True, text=True, timeout=5
    )
    changed_files = [f for f in diff_result.stdout.splitlines() if f.strip()]
except Exception:
    sys.exit(0)

commit_summary = "\n".join(f"  • {c}" for c in commits[:10]) if commits else "  (none found)"
file_summary = "\n".join(f"  • {f}" for f in changed_files[:15]) if changed_files else "  (none found)"

checklist = (
    f"\n📋 PRE-PUSH CHECKLIST — Branch: {branch}\n"
    f"{'='*50}\n\n"
    f"Commits being pushed:\n{commit_summary}\n\n"
    f"Files changed:\n{file_summary}\n\n"
    "Before pushing, confirm:\n"
    "  ✓ Does this branch do exactly ONE thing?\n"
    "  ✓ Is the branch name descriptive of that one thing?\n"
    "  ✓ Are all changed files related to the same feature/fix?\n"
    "  ✓ Have you written a clear PR description ready?\n"
    "  ✓ Are there any debugging artifacts (print statements, TODO hacks) to clean up?\n\n"
    "If any answer is 'no' — consider stopping and tidying before pushing.\n"
)

print(checklist, file=sys.stderr)
# Exit 1 = non-blocking, Claude sees the warning but push proceeds
sys.exit(1)
