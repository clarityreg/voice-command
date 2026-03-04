#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
reports-hub.py — Generate an index page linking all PRP HTML reports.

Scans known report locations under .claude/PRPs/ and htmlcov/,
produces .claude/PRPs/reports-hub.html with links and freshness badges.

Usage:
    uv run scripts/reports-hub.py          # Generate hub and open in browser
    uv run scripts/reports-hub.py --json   # Output report list as JSON (for TUI)
"""

import json
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

# ── Known report locations ───────────────────────────────────────────────────

KNOWN_REPORTS: list[dict] = [
    {
        "name": "Doctor Report",
        "icon": "🏥",
        "path": ".claude/PRPs/doctor/doctor-report.html",
    },
    {
        "name": "Branch Visualization",
        "icon": "🌿",
        "path": ".claude/PRPs/branches/branch-viz.html",
    },
    {
        "name": "Transcript Analysis",
        "icon": "📊",
        "path": ".claude/PRPs/transcript-analysis/report.html",
    },
    {
        "name": "Coverage Report",
        "icon": "📈",
        "path": "htmlcov/index.html",
    },
    {
        "name": "QA Report",
        "icon": "🧪",
        "path": ".claude/PRPs/qa/reports/qa-report.html",
    },
]

QA_REPORT_DIR = ".claude/PRPs/qa/reports"


# ── Helpers ──────────────────────────────────────────────────────────────────

def find_project_root() -> Path:
    """Walk up from script location to find .claude/ directory."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".claude").is_dir():
            return current
        current = current.parent
    return Path.cwd()


def freshness_badge(mtime: datetime) -> dict:
    """Return badge label and class based on file age."""
    now = datetime.now(tz=timezone.utc)
    age_hours = (now - mtime).total_seconds() / 3600

    if age_hours < 24:
        return {"label": "Fresh", "cls": "fresh"}
    if age_hours < 168:  # 7 days
        return {"label": f"{int(age_hours / 24)}d ago", "cls": "recent"}
    return {"label": f"{int(age_hours / 24)}d ago", "cls": "stale"}


def discover_reports(root: Path) -> list[dict]:
    """Find all available reports and collect metadata."""
    reports = []

    for known in KNOWN_REPORTS:
        path = root / known["path"]
        if path.exists():
            stat = path.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            badge = freshness_badge(mtime)
            reports.append({
                "name": known["name"],
                "icon": known["icon"],
                "path": known["path"],
                "abs_path": str(path.resolve()),
                "size_kb": round(stat.st_size / 1024, 1),
                "modified": mtime.strftime("%Y-%m-%d %H:%M"),
                "badge": badge["label"],
                "badge_cls": badge["cls"],
            })

    # Scan QA reports directory
    qa_dir = root / QA_REPORT_DIR
    if qa_dir.is_dir():
        for html_file in sorted(qa_dir.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True):
            stat = html_file.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            badge = freshness_badge(mtime)
            reports.append({
                "name": f"QA: {html_file.stem}",
                "icon": "🧪",
                "path": str(html_file.relative_to(root)),
                "abs_path": str(html_file.resolve()),
                "size_kb": round(stat.st_size / 1024, 1),
                "modified": mtime.strftime("%Y-%m-%d %H:%M"),
                "badge": badge["label"],
                "badge_cls": badge["cls"],
            })

    return reports


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    root = find_project_root()
    reports = discover_reports(root)

    if "--json" in sys.argv:
        print(json.dumps(reports, indent=2))
        return

    if not reports:
        print("No reports found. Run /prp-doctor, /prp-transcript-audit, or /prp-coverage first.")
        return

    # Load HTML template
    template_path = Path(__file__).parent / "reports-hub-template.html"
    if not template_path.exists():
        print(f"Error: Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    template = template_path.read_text(encoding="utf-8")
    data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "report_count": len(reports),
        "reports": reports,
    }
    html = template.replace("{{HUB_DATA}}", json.dumps(data, indent=2))

    output_dir = root / ".claude" / "PRPs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "reports-hub.html"
    output_file.write_text(html, encoding="utf-8")

    print(f"Reports hub: {len(reports)} report(s) found")
    print(f"Saved: {output_file}")

    abs_path = output_file.resolve()
    url = f"file://{abs_path}"
    print(f"Opening: {url}")
    webbrowser.open(url)


if __name__ == "__main__":
    main()
