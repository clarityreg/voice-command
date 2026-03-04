#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
qa-report.py — Generate an HTML QA dashboard from test results, bugs, and quality gates.

Reads test-results.csv and bug files, computes metrics, injects JSON into an
HTML template, and opens the report in the browser.

Usage:
    uv run scripts/qa-report.py                    # Generate HTML, open browser
    uv run scripts/qa-report.py --json             # JSON to stdout (for TUI)
    uv run scripts/qa-report.py --days 7           # Last 7 days (default)
    uv run scripts/qa-report.py --days 30          # Last 30 days
"""

import csv
import json
import re
import sys
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

SETTINGS_FILENAME = ".claude/prp-settings.json"

DEFAULT_QA = {
    "quality_gates": {
        "tests_must_pass": True,
        "min_coverage": 80,
        "max_p0_bugs": 0,
        "max_p1_bugs": 2,
    },
    "tracking_csv": ".claude/PRPs/qa/test-results.csv",
    "bug_dir": ".claude/PRPs/qa/bugs/",
    "report_dir": ".claude/PRPs/qa/reports/",
}


def find_project_root() -> Path:
    """Walk up from script location to find .claude/ directory."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".claude").is_dir():
            return current
        current = current.parent
    return Path.cwd()


def load_settings(project_root: Path) -> dict:
    """Load prp-settings.json and return the qa section."""
    settings_path = project_root / SETTINGS_FILENAME
    if not settings_path.is_file():
        return DEFAULT_QA
    with open(settings_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("qa", DEFAULT_QA)


def get_project_name(project_root: Path) -> str:
    """Get project name from settings or directory name."""
    settings_path = project_root / SETTINGS_FILENAME
    if settings_path.is_file():
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        name = data.get("project", {}).get("name", "")
        if name:
            return name
    return project_root.name


# ── Data collection ──────────────────────────────────────────────────────────


def parse_timestamp(raw: str) -> float | None:
    """Parse a timestamp from either Unix epoch or ISO 8601 format."""
    if not raw:
        return None
    # Try Unix epoch first
    try:
        return float(raw)
    except ValueError:
        pass
    # Try ISO 8601 formats
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except ValueError:
            continue
    return None


def parse_coverage(raw: str | None) -> float | None:
    """Parse coverage from '30%', '30', 'n/a', or None."""
    if raw is None:
        return None
    raw = raw.strip().lower()
    if raw in ("n/a", "", "-"):
        return None
    raw = raw.rstrip("%")
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def parse_duration_ms(row: dict) -> int | None:
    """Parse duration, handling both duration_ms and duration_s columns."""
    # Try duration_ms first (qa-metrics.py format)
    val = row.get("duration_ms")
    if val is not None:
        try:
            return int(val)
        except (ValueError, TypeError):
            pass
    # Try duration_s (prp-qa-init format)
    val = row.get("duration_s")
    if val is not None:
        try:
            return int(float(val) * 1000)
        except (ValueError, TypeError):
            pass
    return None


def read_test_results(csv_path: Path, cutoff_ts: float) -> list[dict]:
    """Read test-results.csv and return rows within the date range.

    Handles two CSV formats:
    - qa-metrics.py:  timestamp (epoch), suite, coverage_pct, duration_ms
    - prp-qa-init:    timestamp (ISO), scope, coverage (with %), duration_s
    """
    if not csv_path.is_file():
        return []

    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = parse_timestamp(row.get("timestamp", ""))
            if ts is None or ts < cutoff_ts:
                continue
            rows.append({
                "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
                "timestamp_raw": ts,
                "suite": row.get("suite") or row.get("scope", ""),
                "total": int(row.get("total", 0)),
                "passed": int(row.get("passed", 0)),
                "failed": int(row.get("failed", 0)),
                "skipped": int(row.get("skipped", 0)),
                "coverage": parse_coverage(row.get("coverage_pct") or row.get("coverage")),
                "duration": parse_duration_ms(row),
            })
    return rows


def scan_bugs(bug_dir: Path) -> dict:
    """Scan bug files and return counts by severity and status."""
    open_by_severity: dict[str, int] = {}
    total_open = 0

    if not bug_dir.is_dir():
        return {"open_by_severity": {}, "open_total": 0}

    for entry in bug_dir.iterdir():
        if not entry.is_file() or not entry.name.endswith(".md"):
            continue
        # Extract severity from filename: P0-xxx.md, P1-xxx.md, etc.
        match = re.match(r"^(P[0-4])", entry.name)
        if match:
            sev = match.group(1)
            # Check if bug is open by reading status line
            status = "OPEN"
            try:
                content = entry.read_text(encoding="utf-8")
                status_match = re.search(r"Status:\s*(OPEN|CLOSED|IN_PROGRESS)", content, re.IGNORECASE)
                if status_match:
                    status = status_match.group(1).upper()
            except OSError:
                pass

            if status != "CLOSED":
                open_by_severity[sev] = open_by_severity.get(sev, 0) + 1
                total_open += 1

    return {"open_by_severity": open_by_severity, "open_total": total_open}


# ── Metric computation ───────────────────────────────────────────────────────


def compute_metrics(rows: list[dict], bugs: dict) -> dict:
    """Compute aggregate metrics from test runs and bug data."""
    if not rows:
        return {
            "pass_rate": None,
            "total_tests": 0,
            "total_passed": 0,
            "coverage": None,
            "coverage_trend": "stable",
            "open_bugs": bugs.get("open_total", 0),
            "p0_bugs": bugs.get("open_by_severity", {}).get("P0", 0),
            "p1_bugs": bugs.get("open_by_severity", {}).get("P1", 0),
            "mttr": None,
            "bugs_resolved_count": 0,
        }

    total_tests = sum(r["total"] for r in rows)
    total_passed = sum(r["passed"] for r in rows)
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0.0

    # Coverage from most recent row
    coverages = [r["coverage"] for r in rows if r["coverage"] is not None]
    latest_coverage = coverages[-1] if coverages else None

    # Coverage trend
    coverage_trend = "stable"
    if len(coverages) >= 2:
        mid = len(coverages) // 2
        first_avg = sum(coverages[:mid]) / mid
        second_avg = sum(coverages[mid:]) / (len(coverages) - mid)
        diff = second_avg - first_avg
        if diff > 1.0:
            coverage_trend = "up"
        elif diff < -1.0:
            coverage_trend = "down"

    return {
        "pass_rate": pass_rate,
        "total_tests": total_tests,
        "total_passed": total_passed,
        "coverage": latest_coverage,
        "coverage_trend": coverage_trend,
        "open_bugs": bugs.get("open_total", 0),
        "p0_bugs": bugs.get("open_by_severity", {}).get("P0", 0),
        "p1_bugs": bugs.get("open_by_severity", {}).get("P1", 0),
        "mttr": None,
        "bugs_resolved_count": 0,
    }


def evaluate_gates(metrics: dict, qa_settings: dict) -> list[dict]:
    """Evaluate quality gates and return status for each."""
    gates_config = qa_settings.get("quality_gates", DEFAULT_QA["quality_gates"])
    gates = []

    # Gate: tests must pass
    if gates_config.get("tests_must_pass", True):
        total_failed = metrics["total_tests"] - metrics["total_passed"]
        gates.append({
            "name": "Tests Pass",
            "threshold": "0 failures",
            "current": f"{total_failed} failures",
            "status": "PASS" if total_failed == 0 else "FAIL",
        })

    # Gate: coverage
    min_cov = gates_config.get("min_coverage", 80)
    current_cov = metrics.get("coverage")
    if current_cov is not None:
        gates.append({
            "name": "Coverage",
            "threshold": f">= {min_cov}%",
            "current": f"{current_cov:.1f}%",
            "status": "PASS" if current_cov >= min_cov else "FAIL",
        })
    else:
        gates.append({
            "name": "Coverage",
            "threshold": f">= {min_cov}%",
            "current": "N/A",
            "status": "WARN",
        })

    # Gate: P0 bugs
    max_p0 = gates_config.get("max_p0_bugs", 0)
    p0 = metrics.get("p0_bugs", 0)
    gates.append({
        "name": "P0 Bugs",
        "threshold": f"<= {max_p0}",
        "current": str(p0),
        "status": "PASS" if p0 <= max_p0 else "FAIL",
    })

    # Gate: P1 bugs
    max_p1 = gates_config.get("max_p1_bugs", 2)
    p1 = metrics.get("p1_bugs", 0)
    gates.append({
        "name": "P1 Bugs",
        "threshold": f"<= {max_p1}",
        "current": str(p1),
        "status": "PASS" if p1 <= max_p1 else "FAIL",
    })

    return gates


def generate_recommendations(metrics: dict, gates: list[dict]) -> list[dict]:
    """Generate actionable recommendations based on current data."""
    recs = []

    failing_gates = [g for g in gates if g["status"] == "FAIL"]
    for g in failing_gates:
        if g["name"] == "Tests Pass":
            recs.append({
                "title": "Fix failing tests",
                "action": "Review test failures and fix before next release.",
            })
        elif g["name"] == "Coverage":
            recs.append({
                "title": "Increase test coverage",
                "action": f"Coverage is below threshold. Run /prp-test on uncovered files.",
            })
        elif g["name"] == "P0 Bugs":
            recs.append({
                "title": "Resolve critical bugs",
                "action": "P0 bugs are release blockers. Prioritize fixes immediately.",
            })
        elif g["name"] == "P1 Bugs":
            recs.append({
                "title": "Address high-severity bugs",
                "action": "P1 bug count exceeds threshold. Plan fixes for the current sprint.",
            })

    if metrics.get("coverage_trend") == "down":
        recs.append({
            "title": "Coverage is declining",
            "action": "New code may be under-tested. Run /prp-qa-init to generate missing tests.",
        })

    if not recs:
        recs.append({
            "title": "All quality gates passing",
            "action": "Continue maintaining test coverage and monitoring for regressions.",
        })

    return recs


def build_coverage_points(rows: list[dict]) -> list[dict]:
    """Build coverage trend points from test run rows."""
    points = []
    prev = None
    for r in rows:
        if r["coverage"] is not None:
            delta = (r["coverage"] - prev) if prev is not None else None
            points.append({
                "date": r["timestamp"],
                "coverage": r["coverage"],
                "delta": delta,
            })
            prev = r["coverage"]
    return points


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Generate QA HTML report")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout instead of HTML")
    parser.add_argument("--days", type=int, default=7, help="Number of days to cover (default: 7)")
    args = parser.parse_args()

    root = find_project_root()
    qa = load_settings(root)
    project_name = get_project_name(root)

    csv_path = root / qa.get("tracking_csv", DEFAULT_QA["tracking_csv"])
    bug_dir = root / qa.get("bug_dir", DEFAULT_QA["bug_dir"])
    report_dir = root / qa.get("report_dir", DEFAULT_QA["report_dir"])

    cutoff = time.time() - (args.days * 86400)
    rows = read_test_results(csv_path, cutoff)
    bugs = scan_bugs(bug_dir)
    metrics = compute_metrics(rows, bugs)
    gates = evaluate_gates(metrics, qa)
    recommendations = generate_recommendations(metrics, gates)
    coverage_points = build_coverage_points(rows)

    overall_status = "PASS"
    if any(g["status"] == "FAIL" for g in gates):
        overall_status = "FAIL"
    elif any(g["status"] == "WARN" for g in gates):
        overall_status = "WARN"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    since_str = datetime.fromtimestamp(cutoff, tz=timezone.utc).strftime("%Y-%m-%d")
    today_str = datetime.now().strftime("%Y-%m-%d")

    data = {
        "project_name": project_name,
        "generated_at": now_str,
        "period": f"{since_str} to {today_str}",
        "days": args.days,
        "overall_status": overall_status,
        "metrics": metrics,
        "quality_gates": gates,
        "test_runs": rows,
        "coverage_points": coverage_points,
        "bugs": {
            "open_by_severity": bugs.get("open_by_severity", {}),
            "open_total": bugs.get("open_total", 0),
            "new_count": 0,
            "closed_count": 0,
        },
        "recommendations": recommendations,
    }

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    # Generate HTML
    template_path = Path(__file__).parent / "qa-report-template.html"
    if not template_path.exists():
        print(f"Error: Template not found: {template_path}", file=sys.stderr)
        return 1

    template = template_path.read_text(encoding="utf-8")
    html = template.replace("{{QA_DATA}}", json.dumps(data, indent=2))

    report_dir.mkdir(parents=True, exist_ok=True)
    output_file = report_dir / "qa-report.html"
    output_file.write_text(html, encoding="utf-8")

    print(f"QA Report: {overall_status}")
    print(f"  Gates: {sum(1 for g in gates if g['status'] == 'PASS')}/{len(gates)} passing")
    if metrics["pass_rate"] is not None:
        print(f"  Pass rate: {metrics['pass_rate']:.1f}%")
    if metrics["coverage"] is not None:
        print(f"  Coverage: {metrics['coverage']:.1f}%")
    print(f"  Open bugs: {bugs.get('open_total', 0)}")
    print(f"Saved: {output_file}")

    abs_path = output_file.resolve()
    url = f"file://{abs_path}"
    print(f"Opening: {url}")
    webbrowser.open(url)

    return 0


if __name__ == "__main__":
    sys.exit(main())
