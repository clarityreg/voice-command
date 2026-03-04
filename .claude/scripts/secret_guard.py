#!/usr/bin/env python3
"""
Secret Guard Hook
-----------------
PreToolUse:Bash hook that blocks commands which would print secret
values to stdout (leaking them into conversation context and transcripts).

ALLOWS running commands with env injection (dotenvx run -- pytest).
BLOCKS commands that dump or print env var values.

Catches:
  - env / printenv (dump all env vars)
  - echo $VAR / printf $VAR (print specific var values)
  - cat/head/tail on .env* files (except .env.example, .env.template)
  - dotenvx run ... -- env/printenv (decrypt + dump)
  - env | grep (pipe env values through filters)
  - export (alone, lists all exports)
  - python -c "...os.environ..." / node -e "...process.env..."

Allows:
  - dotenvx run -- pytest / uv run / python manage.py (run commands with env)
  - Existence checks: [ -n "$VAR" ], test -z "$VAR"
  - Key-only operations: grep -oP '^[A-Z_]+' .env, wc -l .env
  - grep -l (files-with-matches only)
  - Setting vars: export FOO=bar
"""
import json
import re
import sys

data = json.load(sys.stdin)
command = data.get("tool_input", {}).get("command", "")

if not command:
    sys.exit(0)

# ── Safe patterns (exit early) ───────────────────────────────────────────────

# grep -l / --files-with-matches / --count (no values shown)
if re.search(r'grep\s+.*(-l\b|--files-with-matches|--count\b|-c\b)', command):
    sys.exit(0)

# wc on env files (just counts)
if re.search(r'wc\s+.*\.env', command):
    sys.exit(0)

# ── Dangerous patterns ───────────────────────────────────────────────────────

blocked_reason = None

# 1. Standalone env/printenv — dumps all vars
#    Catches: `env`, `env | grep`, `; env`, `&& printenv`
#    Does NOT catch: `dotenvx run -- pytest` (no bare env/printenv)
if re.search(r'(?:^|\||\;|\&\&|\|\|)\s*(?:env|printenv)\s*(?:$|\||\;|\&)', command):
    blocked_reason = "dumps all environment variables to stdout"

# 2. export alone (no assignment) — lists all exports
if not blocked_reason and re.search(r'(?:^|\;|\&\&)\s*export\s*(?:$|\|)', command):
    if not re.search(r'export\s+\w+=', command):
        blocked_reason = "lists all exported variables"

# 3. echo/printf with env var expansion
#    Block: echo $SECRET, echo "$DB_URL", printf "%s" ${API_KEY}
#    Allow: echo "literal", echo "$?", echo SET, echo UNSET
#    Allow: [ -n "$VAR" ] && echo SET (existence check — value never printed)
#
#    Strategy: split on && / || / ; to isolate individual commands,
#    then only flag echo/printf clauses that directly contain $VAR refs.
if not blocked_reason:
    # Split command into clauses on && || ; |
    clauses = re.split(r'\s*(?:\&\&|\|\||\;|\|)\s*', command)
    for clause in clauses:
        clause = clause.strip()
        if not re.match(r'(?:echo|printf)\s', clause):
            continue
        # This clause starts with echo/printf — does it reference a $VAR?
        if re.search(r'\$\{?\w{2,}', clause):
            blocked_reason = "prints environment variable values to stdout"
            break

# 4. cat/head/tail/less/more on .env files (not .env.example/.env.template)
safe_env_pattern = r'\.env\.(?:example|template|sample|test)\b'
if not blocked_reason:
    if re.search(r'(?:cat|head|tail|less|more|bat|strings)\s+.*\.env(?:\.\w+)?', command):
        if not re.search(safe_env_pattern, command):
            blocked_reason = "reads .env file contents (secrets would be visible)"

# 5. grep/rg searching .env file contents (not just filenames)
if not blocked_reason:
    if re.search(r'(?:grep|rg|ag|ack)\s+.*\.env(?:\.\w+)?', command):
        if not re.search(safe_env_pattern, command):
            blocked_reason = "searches .env file contents (use grep -l for filenames only)"

# 6. dotenvx run ... -- env/printenv (decrypt + dump)
if not blocked_reason:
    if re.search(r'dotenvx\s+run\s+.*--\s*(?:env|printenv)\b', command):
        blocked_reason = "decrypts and dumps all environment variables"

# 7. Piping env/printenv into anything
if not blocked_reason:
    if re.search(r'\b(?:env|printenv)\s*\|', command):
        blocked_reason = "pipes environment variable values through a filter"

# 8. Python/node one-liners that access env
if not blocked_reason:
    if re.search(r'python[3]?\s+-c\s+.*os\.environ', command):
        blocked_reason = "dumps environment variables via Python"
    elif re.search(r'node\s+-e\s+.*process\.env', command):
        blocked_reason = "dumps environment variables via Node.js"

# ── Verdict ──────────────────────────────────────────────────────────────────

if blocked_reason:
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"BLOCKED by secret_guard: {blocked_reason}\n\n"
            "Safe alternatives:\n"
            "  Check if set:   [ -n \"$VAR\" ] && echo 'SET' || echo 'UNSET'\n"
            "  Count keys:     grep -c '=' .env\n"
            "  List key names: grep -oP '^[A-Z_]+(?==)' .env\n"
            "  Run with env:   dotenvx run -- pytest tests/\n"
            "  Mask value:     echo \"${VAR:0:4}****\""
        ),
    }))
else:
    sys.exit(0)
