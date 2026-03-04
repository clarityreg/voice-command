#!/usr/bin/env python3
"""QA Test Result Tracking — Append results, summarize trends, check quality gates.

Usage:
  python scripts/qa-metrics.py append --suite <name> --total <n> --passed <n> --failed <n> --skipped <n> --duration <ms> --coverage <pct> --runner <name>
  python scripts/qa-metrics.py summary --days <n>
  python scripts/qa-metrics.py gates
"""

import argparse
import csv
import json
import sys
import time
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

CSV_HEADER = [
    "timestamp",
    "suite",
    "total",
    "passed",
    "failed",
    "skipped",
    "duration_ms",
    "coverage_pct",
    "runner",
]


def find_project_root() -> Path:
    """Walk up from the script location to find the project root (contains .claude/)."""
    candidate = Path(__file__).resolve().parent.parent
    if (candidate / ".claude").is_dir():
        return candidate
    # Fallback: cwd
    cwd = Path.cwd()
    while cwd != cwd.parent:
        if (cwd / ".claude").is_dir():
            return cwd
        cwd = cwd.parent
    return Path(__file__).resolve().parent.parent


def load_settings(project_root: Path) -> dict:
    """Load prp-settings.json and return the qa section."""
    settings_path = project_root / SETTINGS_FILENAME
    if not settings_path.is_file():
        print(f"Warning: {settings_path} not found, using defaults", file=sys.stderr)
        return DEFAULT_QA
    with open(settings_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("qa", DEFAULT_QA)


def resolve_path(project_root: Path, relative: str) -> Path:
    """Resolve a settings-relative path against the project root."""
    return (project_root / relative).resolve()


# ── append ────────────────────────────────────────────────────────────────────


def cmd_append(args, qa_settings: dict, project_root: Path) -> int:
    csv_path = resolve_path(project_root, qa_settings.get("tracking_csv", DEFAULT_QA["tracking_csv"]))
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    write_header = not csv_path.is_file() or csv_path.stat().st_size == 0

    row = {
        "timestamp": int(time.time()),
        "suite": args.suite,
        "total": args.total,
        "passed": args.passed,
        "failed": args.failed,
        "skipped": args.skipped,
        "duration_ms": args.duration,
        "coverage_pct": args.coverage,
        "runner": args.runner,
    }

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    ts_str = datetime.fromtimestamp(row["timestamp"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"Appended: {args.suite} | {args.passed}/{args.total} passed | {args.coverage}% coverage | {ts_str}")
    return 0


# ── summary ───────────────────────────────────────────────────────────────────


def cmd_summary(args, qa_settings: dict, project_root: Path) -> int:
    csv_path = resolve_path(project_root, qa_settings.get("tracking_csv", DEFAULT_QA["tracking_csv"]))

    if not csv_path.is_file():
        print("No test results CSV found. Run tests first.")
        return 1

    cutoff = time.time() - (args.days * 86400)

    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts = int(row["timestamp"])
            except (ValueError, KeyError):
                continue
            if ts >= cutoff:
                rows.append(row)

    if not rows:
        print(f"No test results in the last {args.days} day(s).")
        return 0

    total_runs = len(rows)
    total_tests = sum(int(r.get("total", 0)) for r in rows)
    total_passed = sum(int(r.get("passed", 0)) for r in rows)
    total_failed = sum(int(r.get("failed", 0)) for r in rows)
    total_skipped = sum(int(r.get("skipped", 0)) for r in rows)

    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0.0

    coverages = []
    for r in rows:
        try:
            coverages.append(float(r.get("coverage_pct", 0)))
        except (ValueError, TypeError):
            pass
    avg_coverage = sum(coverages) / len(coverages) if coverages else 0.0

    # Coverage trend: compare first half vs second half
    if len(coverages) >= 2:
        mid = len(coverages) // 2
        first_half_avg = sum(coverages[:mid]) / mid
        second_half_avg = sum(coverages[mid:]) / (len(coverages) - mid)
        diff = second_half_avg - first_half_avg
        if diff > 1.0:
            trend = "up"
        elif diff < -1.0:
            trend = "down"
        else:
            trend = "stable"
    else:
        trend = "stable"

    durations = []
    for r in rows:
        try:
            durations.append(int(r.get("duration_ms", 0)))
        except (ValueError, TypeError):
            pass
    avg_duration = sum(durations) / len(durations) if durations else 0

    # Failure info by suite
    suite_failures = {}
    for r in rows:
        failed = int(r.get("failed", 0))
        if failed > 0:
            suite = r.get("suite", "unknown")
            suite_failures[suite] = suite_failures.get(suite, 0) + failed

    print(f"=== QA Summary (last {args.days} day(s)) ===")
    print()
    print(f"  Total runs:     {total_runs}")
    print(f"  Total tests:    {total_tests}")
    print(f"  Passed:         {total_passed}")
    print(f"  Failed:         {total_failed}")
    print(f"  Skipped:        {total_skipped}")
    print(f"  Pass rate:      {pass_rate:.1f}%")
    print()
    print(f"  Avg coverage:   {avg_coverage:.1f}%")
    print(f"  Coverage trend: {trend}")
    print(f"  Avg duration:   {avg_duration:.0f} ms")

    if suite_failures:
        print()
        print("  Most common failures:")
        for suite, count in sorted(suite_failures.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    - {suite}: {count} failure(s)")

    return 0


# ── gates ─────────────────────────────────────────────────────────────────────


def count_bugs(bug_dir: Path, priority: str) -> int:
    """Count bug files matching a priority prefix (e.g. 'P0-' or 'P1-')."""
    if not bug_dir.is_dir():
        return 0
    prefix = f"{priority}-"
    count = 0
    for entry in bug_dir.iterdir():
        if entry.is_file() and entry.name.startswith(prefix):
            count += 1
    return count


def cmd_gates(qa_settings: dict, project_root: Path) -> int:
    csv_path = resolve_path(project_root, qa_settings.get("tracking_csv", DEFAULT_QA["tracking_csv"]))
    gates = qa_settings.get("quality_gates", DEFAULT_QA["quality_gates"])
    bug_dir = resolve_path(project_root, qa_settings.get("bug_dir", DEFAULT_QA["bug_dir"]))

    if not csv_path.is_file():
        print("GATE SKIP: No test results CSV found. Run tests first.")
        return 1

    # Read last row
    last_row = None
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            last_row = row

    if last_row is None:
        print("GATE SKIP: CSV is empty. Run tests first.")
        return 1

    all_pass = True
    print("=== QA Quality Gates ===")
    print()

    # Gate 1: All tests passed
    failed = int(last_row.get("failed", 0))
    passed = int(last_row.get("passed", 0))
    total = int(last_row.get("total", 0))
    tests_must_pass = gates.get("tests_must_pass", True)

    if tests_must_pass and failed > 0:
        print(f"  FAIL  Tests must pass: {failed}/{total} failed")
        all_pass = False
    else:
        print(f"  PASS  Tests: {passed}/{total} passed, {failed} failed")

    # Gate 2: Coverage threshold
    min_coverage = gates.get("min_coverage", 80)
    try:
        coverage = float(last_row.get("coverage_pct", 0))
    except (ValueError, TypeError):
        coverage = 0.0

    if coverage < min_coverage:
        print(f"  FAIL  Coverage: {coverage:.1f}% < {min_coverage}% minimum")
        all_pass = False
    else:
        print(f"  PASS  Coverage: {coverage:.1f}% >= {min_coverage}% minimum")

    # Gate 3: P0 bugs
    max_p0 = gates.get("max_p0_bugs", 0)
    p0_count = count_bugs(bug_dir, "P0")
    if p0_count > max_p0:
        print(f"  FAIL  P0 bugs: {p0_count} open (max {max_p0})")
        all_pass = False
    else:
        print(f"  PASS  P0 bugs: {p0_count} open (max {max_p0})")

    # Gate 4: P1 bugs
    max_p1 = gates.get("max_p1_bugs", 2)
    p1_count = count_bugs(bug_dir, "P1")
    if p1_count > max_p1:
        print(f"  FAIL  P1 bugs: {p1_count} open (max {max_p1})")
        all_pass = False
    else:
        print(f"  PASS  P1 bugs: {p1_count} open (max {max_p1})")

    print()
    if all_pass:
        print("All quality gates passed.")
        return 0
    else:
        print("One or more quality gates FAILED.")
        return 1


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="QA Test Result Tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # append
    p_append = subparsers.add_parser("append", help="Append a test result row")
    p_append.add_argument("--suite", required=True, help="Test suite name")
    p_append.add_argument("--total", type=int, required=True, help="Total tests")
    p_append.add_argument("--passed", type=int, required=True, help="Passed tests")
    p_append.add_argument("--failed", type=int, required=True, help="Failed tests")
    p_append.add_argument("--skipped", type=int, required=True, help="Skipped tests")
    p_append.add_argument("--duration", type=int, required=True, help="Duration in ms")
    p_append.add_argument("--coverage", type=float, required=True, help="Coverage percentage")
    p_append.add_argument("--runner", required=True, help="Test runner name")

    # summary
    p_summary = subparsers.add_parser("summary", help="Summarize recent results")
    p_summary.add_argument("--days", type=int, default=7, help="Number of days to include (default: 7)")

    # gates
    subparsers.add_parser("gates", help="Check quality gates against latest result")

    parsed = parser.parse_args()
    project_root = find_project_root()
    qa_settings = load_settings(project_root)

    if parsed.command == "append":
        return cmd_append(parsed, qa_settings, project_root)
    elif parsed.command == "summary":
        return cmd_summary(parsed, qa_settings, project_root)
    elif parsed.command == "gates":
        return cmd_gates(qa_settings, project_root)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
