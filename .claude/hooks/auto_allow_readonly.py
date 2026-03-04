#!/usr/bin/env python3
"""
Auto-Allow Readonly Hook (PermissionRequest)
=============================================
Auto-approves read-only operations so they don't trigger permission prompts.
Outputs {"decision": "allow"} for safe tools/commands, or exits silently to
defer to the normal permission prompt for anything else.
"""
import json
import re
import sys


# Tools that are inherently read-only — always safe to auto-approve
READONLY_TOOLS = frozenset({
    "Read", "Glob", "Grep",
    "WebFetch", "WebSearch",
    "ToolSearch",
    "ListMcpResourcesTool", "ReadMcpResourceTool",
    "TaskList", "TaskGet",
})

# Bash command prefixes that are read-only
SAFE_BASH_PREFIXES = (
    "ls", "cat", "head", "tail", "wc", "file",
    "git status", "git log", "git diff", "git branch",
    "git show", "git remote", "git stash list",
    "find", "which", "echo", "pwd", "date", "uname", "whoami",
    "python3 --version", "node --version",
)

# Patterns that indicate a command is NOT read-only
WRITE_INDICATORS = re.compile(
    r"""
    (?:^|\s) sudo \s             |  # sudo anything
    > (?!&)                      |  # redirect (but not >& which is fd redirect in read cmds)
    >> \s                        |  # append redirect
    \| \s* tee \s                |  # pipe to tee
    ; \s* (?:rm|mv|cp|chmod|chown|mkdir|touch|kill|pkill)  |  # chained write cmds
    \$\(                         |  # command substitution $(...)
    `                            |  # backtick command substitution
    -exec \s                     |  # find -exec (can run arbitrary commands)
    \s -[dD] \s                  |  # destructive flags like git branch -D
    \s --force\b                 |  # --force flag
    \s --hard\b                     # --hard flag (git reset --hard)
    """,
    re.VERBOSE,
)


def is_safe_bash(command: str) -> bool:
    """Check if a bash command is read-only."""
    cmd = command.strip()
    if not cmd:
        return False

    # Check for write indicators first (deny-list)
    if WRITE_INDICATORS.search(cmd):
        return False

    # Check if command starts with a safe prefix (allow-list)
    for prefix in SAFE_BASH_PREFIXES:
        if cmd == prefix or cmd.startswith(prefix + " ") or cmd.startswith(prefix + "\t"):
            return True

    return False


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")

    # Auto-allow read-only tools
    if tool_name in READONLY_TOOLS:
        print(json.dumps({"decision": "allow"}))
        sys.exit(0)

    # Auto-allow safe bash commands
    if tool_name == "Bash":
        command = data.get("tool_input", {}).get("command", "")
        if is_safe_bash(command):
            print(json.dumps({"decision": "allow"}))
            sys.exit(0)

    # Everything else: no opinion → normal permission prompt
    sys.exit(0)


if __name__ == "__main__":
    main()
