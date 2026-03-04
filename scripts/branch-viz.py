#!/usr/bin/env python3
"""
branch-viz.py - Generate self-contained HTML branch/PR visualization.

Collects git branch data, PR status via gh CLI, and Plane config from
.claude/prp-settings.json. Injects JSON data into an HTML template that
renders an interactive SVG graph with clickable commit dots and a branch table.
"""

import json
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path


# ── Git helpers ───────────────────────────────────────────────────────────────

def run(cmd: list[str], default: str = "") -> str:
    """Run a shell command and return stdout, or default on failure."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return default


def get_branches() -> list[str]:
    """Return list of local branch names (excluding HEAD)."""
    output = run(["git", "branch", "--format=%(refname:short)"])
    return [b.strip() for b in output.splitlines() if b.strip() and "HEAD" not in b]


def get_main_branch() -> str:
    """Detect the main branch (main or master)."""
    branches = get_branches()
    for candidate in ("main", "master", "develop"):
        if candidate in branches:
            return candidate
    return branches[0] if branches else "main"


def get_ahead_behind(branch: str, base: str) -> tuple[int, int]:
    """Return (ahead, behind) count relative to base branch."""
    if branch == base:
        return 0, 0
    output = run(["git", "rev-list", "--left-right", "--count", f"{base}...{branch}"])
    parts = output.split()
    if len(parts) == 2:
        try:
            return int(parts[1]), int(parts[0])
        except ValueError:
            pass
    return 0, 0


def get_last_commit(branch: str) -> dict:
    """Return dict with hash, message, author, date for last commit on branch."""
    fmt = "%H|%s|%an|%ar"
    output = run(["git", "log", "--format=" + fmt, "-1", branch])
    if output:
        parts = output.split("|", 3)
        if len(parts) == 4:
            return {
                "hash": parts[0][:7],
                "message": parts[1],
                "author": parts[2],
                "relative": parts[3],
            }
    return {"hash": "", "message": "", "author": "", "relative": ""}


def get_remote_url() -> str:
    """Return origin remote URL."""
    return run(["git", "remote", "get-url", "origin"])


def derive_github_base_url(remote_url: str) -> str:
    """Convert git remote URL to HTTPS GitHub URL."""
    url = remote_url
    if url.startswith("git@github.com:"):
        url = url.replace("git@github.com:", "https://github.com/")
    if url.endswith(".git"):
        url = url[:-4]
    return url


def get_commit_graph(branches: list[str], main: str) -> tuple[list[dict], list[dict]]:
    """Build structured commit data for all branches.

    Returns (branch_data, fork_points) where:
    - branch_data: list of dicts with name, isMain, commits, ahead, behind
    - fork_points: list of dicts with branch, fromCommit, parentBranch
    """
    branch_data = []
    fork_points = []

    # Collect main branch commits first
    main_log = run([
        "git", "log", "--format=%H|%s|%an|%aI|%ar", "-15", main,
    ])
    main_commits = []
    for line in main_log.splitlines():
        parts = line.split("|", 4)
        if len(parts) == 5:
            main_commits.append({
                "hash": parts[0],
                "message": parts[1],
                "author": parts[2],
                "date": parts[3],
                "relativeDate": parts[4],
            })
    # Reverse so oldest is first (for left-to-right drawing)
    main_commits.reverse()

    branch_data.append({
        "name": main,
        "isMain": True,
        "commits": main_commits,
        "ahead": 0,
        "behind": 0,
    })

    # Collect feature branch commits
    for branch in sorted(branches):
        if branch == main:
            continue

        ahead, behind = get_ahead_behind(branch, main)

        # Get the merge-base (fork point)
        fork_hash = run(["git", "merge-base", main, branch])

        # Get commits unique to this branch (since fork point)
        branch_log = run([
            "git", "log", "--format=%H|%s|%an|%aI|%ar",
            f"{main}..{branch}", "-10",
        ])
        commits = []
        for line in branch_log.splitlines():
            parts = line.split("|", 4)
            if len(parts) == 5:
                commits.append({
                    "hash": parts[0],
                    "message": parts[1],
                    "author": parts[2],
                    "date": parts[3],
                    "relativeDate": parts[4],
                })
        commits.reverse()

        branch_data.append({
            "name": branch,
            "isMain": False,
            "commits": commits,
            "ahead": ahead,
            "behind": behind,
        })

        if fork_hash:
            fork_points.append({
                "branch": branch,
                "fromCommit": fork_hash,
                "parentBranch": main,
            })

    return branch_data, fork_points


# ── GitHub PR data ────────────────────────────────────────────────────────────

def get_pr_data() -> dict[str, dict]:
    """Return dict keyed by branch name with PR info."""
    if not run(["which", "gh"]):
        return {}
    output = run([
        "gh", "pr", "list",
        "--json", "number,title,state,headRefName,url,isDraft",
        "--limit", "50",
    ])
    if not output:
        return {}
    try:
        prs = json.loads(output)
    except json.JSONDecodeError:
        return {}

    result: dict[str, dict] = {}
    for pr in prs:
        branch = pr.get("headRefName", "")
        if branch:
            result[branch] = {
                "number": pr.get("number"),
                "title": pr.get("title", ""),
                "state": pr.get("state", "").upper(),
                "url": pr.get("url", ""),
                "draft": pr.get("isDraft", False),
            }
    return result


# ── Settings ──────────────────────────────────────────────────────────────────

def load_plane_config() -> dict:
    """Load Plane config from .claude/prp-settings.json."""
    settings_path = Path(".claude/prp-settings.json")
    if not settings_path.exists():
        return {}
    try:
        data = json.loads(settings_path.read_text())
        return data.get("plane", {})
    except (json.JSONDecodeError, OSError):
        return {}


# ── Output assembly ──────────────────────────────────────────────────────────

def build_output_data(
    branch_data: list[dict],
    fork_points: list[dict],
    prs: dict[str, dict],
    github_base: str,
    plane_config: dict,
) -> dict:
    """Assemble all data into a single JSON-serializable dict."""
    return {
        "branches": branch_data,
        "forkPoints": fork_points,
        "prs": prs,
        "githubBase": github_base,
        "plane": plane_config,
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if not Path(".git").exists():
        print("Error: Not in a git repository root.", file=sys.stderr)
        sys.exit(1)

    print("Collecting branch data...")
    branches = get_branches()
    if not branches:
        print("No branches found.", file=sys.stderr)
        sys.exit(1)

    main_branch = get_main_branch()
    print(f"  Main branch: {main_branch}")
    print(f"  Local branches: {len(branches)}")

    print("Fetching PR data...")
    prs = get_pr_data()
    print(f"  Open PRs found: {len(prs)}")

    remote_url = get_remote_url()
    github_base = derive_github_base_url(remote_url) if remote_url else ""

    print("Loading Plane config...")
    plane_config = load_plane_config()
    if plane_config.get("workspace_slug"):
        print(f"  Plane workspace: {plane_config['workspace_slug']}")
    else:
        print("  Plane not configured (skipping task creation buttons)")

    print("Building commit graph...")
    branch_data, fork_points = get_commit_graph(branches, main_branch)

    print("Generating HTML...")
    data = build_output_data(branch_data, fork_points, prs, github_base, plane_config)
    data_json = json.dumps(data, indent=2)

    # Load template
    template_path = Path(__file__).parent / "branch-viz-template.html"
    if not template_path.exists():
        print(f"Error: Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)
    template = template_path.read_text(encoding="utf-8")

    # Inject data
    html = template.replace("{{GRAPH_DATA}}", data_json)

    # Write output
    output_dir = Path(".claude/PRPs/branches")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "branch-viz.html"
    output_file.write_text(html, encoding="utf-8")

    print(f"\nBranch visualization saved: {output_file}")

    # Open in browser
    abs_path = output_file.resolve()
    url = f"file://{abs_path}"
    print(f"Opening: {url}")
    webbrowser.open(url)


if __name__ == "__main__":
    main()
