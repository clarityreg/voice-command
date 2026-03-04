#!/usr/bin/env python3
"""
Detect significant file changes in backend/ or frontend/ and POST a webhook.

Usage:
    python .claude/hooks/structure_change.py --webhook-url http://localhost:3001/api/hooks/claude-code
Optional flags:
    --base-ref origin/main   # Git ref to diff against (default)
    --threshold 50           # Min changed lines (add+del) to count as significant
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

from decouple import Config, RepositoryEnv


@dataclass
class FileChange:
    path: str
    added: int
    deleted: int

    @property
    def total(self) -> int:
        return self.added + self.deleted


def run_git_diff(base_ref: str) -> List[FileChange]:
    """Return parsed git diff --numstat results from base_ref to working tree."""
    try:
        result = subprocess.run(
            ["git", "diff", "--numstat", base_ref],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"git diff failed for base ref '{base_ref}': {exc.stderr}") from exc

    changes: List[FileChange] = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added_str, deleted_str, path = parts
        try:
            added = int(added_str)
            deleted = int(deleted_str)
        except ValueError:
            # Binary files show '-' counts; record with zero changes for threshold filtering
            added = 0
            deleted = 0
        changes.append(FileChange(path=path, added=added, deleted=deleted))
    return changes


def filter_significant(
    changes: List[FileChange], threshold: int
) -> Dict[str, List[FileChange]]:
    """Filter changes by directory (backend/frontend) above threshold."""
    buckets: Dict[str, List[FileChange]] = {"backend": [], "frontend": []}
    for change in changes:
        for directory in buckets.keys():
            if change.path.startswith(f"{directory}/") and change.total >= threshold:
                buckets[directory].append(change)
                break
    return {k: v for k, v in buckets.items() if v}


def current_branch() -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        branch = result.stdout.strip()
        return branch if branch else None
    except subprocess.CalledProcessError:
        return None


def post_webhook(url: str, payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=10) as resp:
            resp.read()  # Drain response
    except HTTPError as exc:
        raise RuntimeError(
            f"Webhook HTTP error {exc.code}: {exc.read().decode('utf-8', 'ignore')}") from exc
    except URLError as exc:
        raise RuntimeError(f"Webhook connection error: {exc.reason}") from exc


def load_webhook_from_env(root: Path) -> Optional[str]:
    env_path = root / ".env"
    if not env_path.exists():
        return None
    cfg = Config(repository=RepositoryEnv(str(env_path)))
    return cfg("VISUALIZER_WEBHOOK", default=None)


def structure_change(
    webhook_url: Optional[str],
    base_ref: str = "origin/main",
    threshold: int = 50,
) -> int:
    """Detect significant backend/frontend changes and send a webhook."""
    try:
        changes = run_git_diff(base_ref)
    except RuntimeError as original_error:
        # Fallback to previous commit if base_ref missing locally
        sys.stderr.write(
            f"Warning: git diff failed for '{base_ref}': {original_error}. Falling back to HEAD~1.\n")
        try:
            changes = run_git_diff("HEAD~1")
            base_ref = "HEAD~1"
        except RuntimeError as fallback_error:
            raise RuntimeError(
                f"git diff failed for both '{base_ref}' ({original_error}) and 'HEAD~1' ({fallback_error})"
            ) from fallback_error

    significant = filter_significant(changes, threshold)
    if not significant:
        return 0

    if not webhook_url:
        project_root = Path(__file__).resolve().parents[2]
        webhook_url = load_webhook_from_env(project_root)
    if not webhook_url:
        raise RuntimeError(
            "No webhook URL provided. Set VISUALIZER_WEBHOOK in .env or pass --webhook-url.")

    payload = {
        "project": "clarity-information",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "branch": current_branch(),
        "base_ref": base_ref,
        "threshold": threshold,
        "directories": [
            {
                "name": name,
                "files": [
                    {"path": fc.path, "added": fc.added,
                        "deleted": fc.deleted, "total": fc.total}
                    for fc in files
                ],
            }
            for name, files in significant.items()
        ],
    }

    post_webhook(webhook_url, payload)
    return len(significant)


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send webhook on significant backend/frontend changes.")
    parser.add_argument(
        "--webhook-url",
        required=False,
        help="Webhook URL to POST change details (overrides VISUALIZER_WEBHOOK in .env).",
    )
    parser.add_argument("--base-ref", default="origin/main",
                        help="Git ref to diff against (default: origin/main).")
    parser.add_argument(
        "--threshold",
        type=int,
        default=50,
        help="Minimum changed lines (added+deleted) to trigger webhook (default: 50).",
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    try:
        sent = structure_change(
            args.webhook_url, base_ref=args.base_ref, threshold=args.threshold)
    except Exception as exc:  # noqa: BLE001
        # Log but don't fail - this hook is non-critical and shouldn't block Claude
        sys.stderr.write(f"structure_change warning: {exc}\n")
        return 0  # Return success to not block Claude workflow

    if sent == 0:
        sys.stdout.write(
            "No significant changes detected; webhook not sent.\n")
    else:
        sys.stdout.write(f"Webhook sent for {sent} directory groups.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
