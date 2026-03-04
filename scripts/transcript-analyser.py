#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
transcript-analyser.py — Mine Claude Code session transcripts for failure signals.

Scans JSONL transcripts for language patterns that indicate context failures:
apologies, self-corrections, confusion, context loss, backtracking, and
repeated tool failures. Produces JSON, markdown, or HTML reports.

Usage:
    uv run scripts/transcript-analyser.py scan [--since YYYY-MM-DD] [--days N] [--format json|markdown]
    uv run scripts/transcript-analyser.py report [--since YYYY-MM-DD] [--days N]
"""

import argparse
import json
import re
import subprocess
import sys
import webbrowser
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Generator

# ── Signal categories ────────────────────────────────────────────────────────

SIGNAL_CATEGORIES: dict[str, dict] = {
    "apologies": {
        "severity": "medium",
        "label": "Apologies",
        "patterns": [
            r"\bI'm sorry\b",
            r"\bI apologise\b",
            r"\bI apologize\b",
            r"\bmy apologies\b",
            r"\bmy mistake\b",
        ],
    },
    "self_corrections": {
        "severity": "high",
        "label": "Self-Corrections",
        "patterns": [
            r"\byou're absolutely right\b",
            r"\byou're correct\b",
            r"\bI was wrong\b",
            r"\blet me try again\b",
            r"\bactually,? I should\b",
            r"\bI stand corrected\b",
        ],
    },
    "confusion": {
        "severity": "medium",
        "label": "Confusion",
        "patterns": [
            r"\bI'm not sure (?:why|how|what|if)\b",
            r"\bthis is unexpected\b",
            r"\bI'm confused\b",
            r"\bI don't understand why\b",
        ],
    },
    "context_loss": {
        "severity": "high",
        "label": "Context Loss",
        "patterns": [
            r"\bcould you remind me\b",
            r"\bI don't have context\b",
            r"\bI (?:may have )?lost track\b",
            r"\bas (?:you |we )?mentioned earlier\b",
        ],
    },
    "backtracking": {
        "severity": "medium",
        "label": "Backtracking",
        "patterns": [
            r"\blet me reconsider\b",
            r"\bon second thought\b",
            r"\blet me start over\b",
            r"\blet me take a different approach\b",
            r"\bI need to rethink\b",
        ],
    },
}

# Compile all patterns once
_COMPILED_PATTERNS: dict[str, list[re.Pattern]] = {}
for _cat, _cfg in SIGNAL_CATEGORIES.items():
    _COMPILED_PATTERNS[_cat] = [re.compile(p, re.IGNORECASE) for p in _cfg["patterns"]]


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class Signal:
    category: str
    severity: str
    pattern: str
    matched_text: str
    context: str  # surrounding text (trimmed)
    session_id: str
    timestamp: str


@dataclass
class ToolFailure:
    tool_name: str
    error_message: str
    consecutive_count: int
    failure_type: str  # "repeated_failure" or "hallucination"
    session_id: str
    timestamp: str


@dataclass
class SessionAnalysis:
    session_id: str
    transcript_path: str
    message_count: int
    signals: list[Signal] = field(default_factory=list)
    tool_failures: list[ToolFailure] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""


@dataclass
class Recommendation:
    target: str  # "CLAUDE.md", "Hook/Skill", "Command/Plan", etc.
    action: str
    reason: str
    severity: str
    signal_count: int


@dataclass
class AnalysisReport:
    generated_at: str
    transcript_count: int
    total_messages: int
    date_range: str
    sessions: list[dict] = field(default_factory=list)
    category_totals: dict = field(default_factory=dict)
    tool_failure_totals: dict = field(default_factory=dict)
    top_patterns: list[dict] = field(default_factory=list)
    recommendations: list[dict] = field(default_factory=list)
    severity_counts: dict = field(default_factory=dict)


# ── Path discovery ───────────────────────────────────────────────────────────

def find_project_root() -> Path:
    """Walk up from script location to find .claude/ directory."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".claude").is_dir():
            return current
        current = current.parent
    # Fallback: current working directory
    cwd = Path.cwd()
    if (cwd / ".claude").is_dir():
        return cwd
    return cwd


def discover_transcripts(project_root: Path, since: datetime | None) -> list[Path]:
    """Find JSONL transcript files from Claude project directories and backups."""
    transcripts: list[Path] = []

    # Source 1: ~/.claude/projects/*/*.jsonl
    claude_dir = Path.home() / ".claude" / "projects"
    if claude_dir.is_dir():
        for project_dir in claude_dir.iterdir():
            if not project_dir.is_dir():
                continue
            for jsonl_file in project_dir.glob("*.jsonl"):
                if _file_in_range(jsonl_file, since):
                    transcripts.append(jsonl_file)

    # Source 2: .claude/transcripts/*.json (backup references)
    backup_dir = project_root / ".claude" / "transcripts"
    if backup_dir.is_dir():
        for backup_file in backup_dir.glob("*.json"):
            try:
                data = json.loads(backup_file.read_text())
                transcript_path = data.get("transcript_path", "")
                if transcript_path:
                    p = Path(transcript_path)
                    if p.exists() and p.suffix == ".jsonl":
                        if _file_in_range(p, since):
                            transcripts.append(p)
            except (json.JSONDecodeError, OSError, KeyError):
                continue

    # Deduplicate by resolved path
    seen = set()
    unique = []
    for t in transcripts:
        resolved = t.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(t)

    return sorted(unique, key=lambda p: p.stat().st_mtime, reverse=True)


def _file_in_range(path: Path, since: datetime | None) -> bool:
    """Check if a file's modification time is within the date range."""
    if since is None:
        return True
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        return mtime >= since
    except OSError:
        return False


# ── JSONL parsing ────────────────────────────────────────────────────────────

def parse_jsonl_transcript(path: Path) -> Generator[dict, None, None]:
    """Yield parsed JSON entries from a JSONL file, line-by-line."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return


# ── Signal extraction ────────────────────────────────────────────────────────

def extract_text_signals(entries: list[dict], session_id: str) -> list[Signal]:
    """Scan assistant text blocks for failure-signal patterns."""
    signals: list[Signal] = []

    for entry in entries:
        if entry.get("type") != "assistant":
            continue

        timestamp = entry.get("timestamp", "")
        message = entry.get("message", {})
        content = message.get("content", [])

        if isinstance(content, str):
            content = [{"type": "text", "text": content}]

        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "text":
                continue
            text = block.get("text", "")
            if not text:
                continue

            for category, patterns in _COMPILED_PATTERNS.items():
                cfg = SIGNAL_CATEGORIES[category]
                for pattern in patterns:
                    for match in pattern.finditer(text):
                        # Extract surrounding context (±80 chars)
                        start = max(0, match.start() - 80)
                        end = min(len(text), match.end() + 80)
                        context = text[start:end].replace("\n", " ").strip()
                        if start > 0:
                            context = "..." + context
                        if end < len(text):
                            context = context + "..."

                        signals.append(Signal(
                            category=category,
                            severity=cfg["severity"],
                            pattern=pattern.pattern,
                            matched_text=match.group(),
                            context=context,
                            session_id=session_id,
                            timestamp=timestamp,
                        ))

    return signals


def extract_tool_failures(entries: list[dict], session_id: str) -> list[ToolFailure]:
    """Detect repeated tool failures and hallucinated file paths."""
    failures: list[ToolFailure] = []

    # Track consecutive errors per tool
    consecutive_errors: dict[str, list[dict]] = defaultdict(list)
    last_tool_use: dict[str, dict] = {}

    hallucination_patterns = [
        re.compile(r"does not exist", re.IGNORECASE),
        re.compile(r"not found", re.IGNORECASE),
        re.compile(r"no such file", re.IGNORECASE),
        re.compile(r"ENOENT", re.IGNORECASE),
    ]

    for entry in entries:
        entry_type = entry.get("type", "")
        message = entry.get("message", {})
        content = message.get("content", [])
        timestamp = entry.get("timestamp", "")

        if isinstance(content, str):
            content = [{"type": "text", "text": content}]

        if not isinstance(content, list):
            continue

        for block in content:
            if not isinstance(block, dict):
                continue

            # Track tool_use calls
            if block.get("type") == "tool_use":
                tool_name = block.get("name", "unknown")
                last_tool_use[tool_name] = {
                    "timestamp": timestamp,
                    "input": block.get("input", {}),
                }

            # Check tool_result errors
            if block.get("type") == "tool_result" and block.get("is_error"):
                error_content = block.get("content", "")
                if isinstance(error_content, list):
                    error_content = " ".join(
                        b.get("text", "") for b in error_content
                        if isinstance(b, dict) and b.get("type") == "text"
                    )

                # Determine tool name from tool_use_id
                tool_use_id = block.get("tool_use_id", "")
                tool_name = "unknown"
                for name, info in last_tool_use.items():
                    tool_name = name
                    break

                consecutive_errors[tool_name].append({
                    "error": str(error_content)[:200],
                    "timestamp": timestamp,
                })

                # Check for hallucinations (Read/Glob errors about missing files)
                if tool_name in ("Read", "Glob", "Grep"):
                    for hp in hallucination_patterns:
                        if hp.search(str(error_content)):
                            failures.append(ToolFailure(
                                tool_name=tool_name,
                                error_message=str(error_content)[:200],
                                consecutive_count=1,
                                failure_type="hallucination",
                                session_id=session_id,
                                timestamp=timestamp,
                            ))
                            break

            # Successful tool_result resets consecutive counter for that tool
            elif block.get("type") == "tool_result" and not block.get("is_error"):
                # Check if any tool had 3+ consecutive errors before this success
                for tool_name, errors in list(consecutive_errors.items()):
                    if len(errors) >= 3:
                        failures.append(ToolFailure(
                            tool_name=tool_name,
                            error_message=errors[0]["error"],
                            consecutive_count=len(errors),
                            failure_type="repeated_failure",
                            session_id=session_id,
                            timestamp=errors[0]["timestamp"],
                        ))
                consecutive_errors.clear()

    # Check remaining consecutive errors at end of session
    for tool_name, errors in consecutive_errors.items():
        if len(errors) >= 3:
            failures.append(ToolFailure(
                tool_name=tool_name,
                error_message=errors[0]["error"],
                consecutive_count=len(errors),
                failure_type="repeated_failure",
                session_id=session_id,
                timestamp=errors[0]["timestamp"],
            ))

    return failures


# ── Session analysis ─────────────────────────────────────────────────────────

def analyse_session(jsonl_path: Path) -> SessionAnalysis:
    """Combine text signal + tool failure analysis for one session."""
    entries = list(parse_jsonl_transcript(jsonl_path))
    if not entries:
        return SessionAnalysis(
            session_id="unknown",
            transcript_path=str(jsonl_path),
            message_count=0,
        )

    session_id = entries[0].get("sessionId", jsonl_path.stem)
    timestamps = [e.get("timestamp", "") for e in entries if e.get("timestamp")]
    start_time = timestamps[0] if timestamps else ""
    end_time = timestamps[-1] if timestamps else ""

    signals = extract_text_signals(entries, session_id)
    tool_failures = extract_tool_failures(entries, session_id)

    return SessionAnalysis(
        session_id=session_id,
        transcript_path=str(jsonl_path),
        message_count=len(entries),
        signals=signals,
        tool_failures=tool_failures,
        start_time=start_time,
        end_time=end_time,
    )


# ── Recommendations ──────────────────────────────────────────────────────────

def generate_recommendations(sessions: list[SessionAnalysis]) -> list[Recommendation]:
    """Map signal clusters to improvement targets."""
    recommendations: list[Recommendation] = []

    # Aggregate counts
    category_counts: Counter = Counter()
    tool_failure_counts: Counter = Counter()
    hallucination_count = 0

    for session in sessions:
        for signal in session.signals:
            category_counts[signal.category] += 1
        for failure in session.tool_failures:
            if failure.failure_type == "hallucination":
                hallucination_count += 1
            else:
                tool_failure_counts[failure.tool_name] += 1

    # High self-correction rate → improve CLAUDE.md
    if category_counts["self_corrections"] >= 3:
        recommendations.append(Recommendation(
            target="CLAUDE.md",
            action="Add explicit documentation about usage patterns and conventions",
            reason=f"{category_counts['self_corrections']} self-correction signals detected",
            severity="high",
            signal_count=category_counts["self_corrections"],
        ))

    # Repeated tool failures → create validation hook
    for tool_name, count in tool_failure_counts.most_common(3):
        if count >= 2:
            recommendations.append(Recommendation(
                target="Hook/Skill",
                action=f"Create validation hook or pre-use check for {tool_name}",
                reason=f"{count} repeated failure clusters on {tool_name}",
                severity="high",
                signal_count=count,
            ))

    # Context loss → improve priming
    if category_counts["context_loss"] >= 2:
        recommendations.append(Recommendation(
            target="Skill",
            action="Update prp-context-enricher or add priming for commonly lost context",
            reason=f"{category_counts['context_loss']} context loss signals detected",
            severity="high",
            signal_count=category_counts["context_loss"],
        ))

    # Hallucinations on file paths → document structure
    if hallucination_count >= 3:
        recommendations.append(Recommendation(
            target="CLAUDE.md",
            action="Document project structure and key file paths more explicitly",
            reason=f"{hallucination_count} file path hallucinations detected",
            severity="high",
            signal_count=hallucination_count,
        ))

    # Backtracking → improve plan templates
    if category_counts["backtracking"] >= 3:
        recommendations.append(Recommendation(
            target="Command/Plan",
            action="Improve plan templates to reduce ambiguity in affected areas",
            reason=f"{category_counts['backtracking']} backtracking signals detected",
            severity="medium",
            signal_count=category_counts["backtracking"],
        ))

    # High apology rate → add explicit guidance
    if category_counts["apologies"] >= 5:
        recommendations.append(Recommendation(
            target="CLAUDE.md / Skill",
            action="Add explicit guidance for domains where apologies cluster",
            reason=f"{category_counts['apologies']} apology signals detected",
            severity="medium",
            signal_count=category_counts["apologies"],
        ))

    # Confusion signals → add documentation
    if category_counts["confusion"] >= 2:
        recommendations.append(Recommendation(
            target="CLAUDE.md",
            action="Clarify documentation for areas where confusion signals appear",
            reason=f"{category_counts['confusion']} confusion signals detected",
            severity="medium",
            signal_count=category_counts["confusion"],
        ))

    return sorted(recommendations, key=lambda r: (0 if r.severity == "high" else 1, -r.signal_count))


# ── Report building ──────────────────────────────────────────────────────────

def build_report(sessions: list[SessionAnalysis], date_range: str) -> dict:
    """Assemble a full analysis report from session analyses."""
    category_totals: Counter = Counter()
    severity_counts: Counter = Counter()
    pattern_counter: Counter = Counter()
    tool_failure_totals: Counter = Counter()
    total_messages = 0

    for session in sessions:
        total_messages += session.message_count
        for signal in session.signals:
            category_totals[signal.category] += 1
            severity_counts[signal.severity] += 1
            pattern_counter[signal.matched_text.lower()] += 1
        for failure in session.tool_failures:
            key = f"{failure.tool_name} ({failure.failure_type})"
            tool_failure_totals[key] += 1

    recommendations = generate_recommendations(sessions)

    # Top patterns
    top_patterns = [
        {"pattern": pat, "count": count}
        for pat, count in pattern_counter.most_common(10)
    ]

    # Per-session summaries
    session_summaries = []
    for s in sessions:
        if s.signals or s.tool_failures:
            cat_counts = Counter(sig.category for sig in s.signals)
            session_summaries.append({
                "session_id": s.session_id,
                "transcript_path": s.transcript_path,
                "message_count": s.message_count,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "signal_count": len(s.signals),
                "tool_failure_count": len(s.tool_failures),
                "category_counts": dict(cat_counts),
                "signals": [asdict(sig) for sig in s.signals[:20]],  # cap per session
                "tool_failures": [asdict(f) for f in s.tool_failures[:10]],
            })

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "transcript_count": len(sessions),
        "total_messages": total_messages,
        "date_range": date_range,
        "category_totals": {
            cat: {
                "count": category_totals.get(cat, 0),
                "severity": cfg["severity"],
                "label": cfg["label"],
            }
            for cat, cfg in SIGNAL_CATEGORIES.items()
        },
        "tool_failure_totals": dict(tool_failure_totals),
        "top_patterns": top_patterns,
        "severity_counts": dict(severity_counts),
        "recommendations": [asdict(r) for r in recommendations],
        "sessions": sorted(session_summaries, key=lambda s: s["signal_count"], reverse=True),
    }


# ── Output formatters ────────────────────────────────────────────────────────

def format_markdown(report: dict) -> str:
    """Format report as readable markdown."""
    lines = []
    lines.append("# Transcript Analysis Report")
    lines.append(f"\n**Generated:** {report['generated_at']}")
    lines.append(f"**Transcripts scanned:** {report['transcript_count']}")
    lines.append(f"**Total messages:** {report['total_messages']}")
    lines.append(f"**Date range:** {report['date_range']}")

    # Summary
    lines.append("\n## Signal Summary\n")
    total_signals = sum(c["count"] for c in report["category_totals"].values())
    lines.append(f"**Total signals found:** {total_signals}")
    lines.append("")
    lines.append("| Category | Count | Severity |")
    lines.append("|----------|-------|----------|")
    for cat, info in report["category_totals"].items():
        if info["count"] > 0:
            lines.append(f"| {info['label']} | {info['count']} | {info['severity']} |")

    # Tool failures
    if report["tool_failure_totals"]:
        lines.append("\n## Tool Failures\n")
        lines.append("| Tool (Type) | Count |")
        lines.append("|-------------|-------|")
        for key, count in sorted(report["tool_failure_totals"].items(), key=lambda x: -x[1]):
            lines.append(f"| {key} | {count} |")

    # Top patterns
    if report["top_patterns"]:
        lines.append("\n## Top Patterns\n")
        for i, p in enumerate(report["top_patterns"][:10], 1):
            lines.append(f"{i}. **\"{p['pattern']}\"** — {p['count']} occurrences")

    # Recommendations
    if report["recommendations"]:
        lines.append("\n## Recommendations\n")
        lines.append("| Severity | Target | Action | Signals |")
        lines.append("|----------|--------|--------|---------|")
        for rec in report["recommendations"]:
            sev = rec["severity"].upper()
            lines.append(f"| {sev} | {rec['target']} | {rec['action']} | {rec['signal_count']} |")

    # Per-session breakdown
    if report["sessions"]:
        lines.append("\n## Sessions with Signals\n")
        for s in report["sessions"][:15]:
            sid = s["session_id"][:12] + "..." if len(s["session_id"]) > 12 else s["session_id"]
            lines.append(f"\n### Session {sid}")
            lines.append(f"- Messages: {s['message_count']}")
            lines.append(f"- Signals: {s['signal_count']}, Tool failures: {s['tool_failure_count']}")
            if s.get("start_time"):
                lines.append(f"- Time: {s['start_time'][:19]}")
            if s["signals"]:
                lines.append("\n**Sample signals:**")
                for sig in s["signals"][:5]:
                    lines.append(f"- [{sig['category']}] \"{sig['matched_text']}\" — _{sig['context'][:100]}_")

    return "\n".join(lines)


# ── Subcommands ──────────────────────────────────────────────────────────────

def cmd_scan(args: argparse.Namespace) -> None:
    """Scan transcripts and output results."""
    project_root = find_project_root()
    since = _parse_since(args)
    date_range = _date_range_label(args)

    transcripts = discover_transcripts(project_root, since)
    if not transcripts:
        print("No transcripts found in the specified date range.", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {len(transcripts)} transcript(s)...", file=sys.stderr)

    sessions = []
    for i, path in enumerate(transcripts):
        if (i + 1) % 10 == 0:
            print(f"  ...processed {i + 1}/{len(transcripts)}", file=sys.stderr)
        sessions.append(analyse_session(path))

    report = build_report(sessions, date_range)

    fmt = getattr(args, "format", "json")
    if fmt == "json":
        print(json.dumps(report, indent=2))
    elif fmt == "markdown":
        print(format_markdown(report))
    else:
        print(json.dumps(report, indent=2))


def cmd_report(args: argparse.Namespace) -> None:
    """Generate HTML report and open in browser."""
    project_root = find_project_root()
    since = _parse_since(args)
    date_range = _date_range_label(args)

    transcripts = discover_transcripts(project_root, since)
    if not transcripts:
        print("No transcripts found in the specified date range.", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {len(transcripts)} transcript(s)...")

    sessions = []
    for i, path in enumerate(transcripts):
        if (i + 1) % 10 == 0:
            print(f"  ...processed {i + 1}/{len(transcripts)}")
        sessions.append(analyse_session(path))

    report = build_report(sessions, date_range)
    data_json = json.dumps(report, indent=2)

    # Load HTML template
    template_path = Path(__file__).parent / "transcript-analyser-template.html"
    if not template_path.exists():
        print(f"Error: Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    template = template_path.read_text(encoding="utf-8")
    html = template.replace("{{ANALYSER_DATA}}", data_json)

    # Save report
    output_dir = project_root / ".claude" / "PRPs" / "transcript-analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "report.html"
    output_file.write_text(html, encoding="utf-8")

    # Save JSON artifact
    json_file = output_dir / "latest.json"
    json_file.write_text(data_json, encoding="utf-8")

    total_signals = sum(c["count"] for c in report["category_totals"].values())
    total_failures = sum(report["tool_failure_totals"].values())
    print(f"\nAnalysis complete: {total_signals} signals, {total_failures} tool failures")
    print(f"  across {report['transcript_count']} sessions ({report['total_messages']} messages)")
    print(f"Saved: {output_file}")
    print(f"JSON:  {json_file}")

    abs_path = output_file.resolve()
    url = f"file://{abs_path}"
    print(f"Opening: {url}")
    webbrowser.open(url)

    # Regenerate reports hub if available
    hub_script = Path(__file__).parent / "reports-hub.py"
    if hub_script.exists():
        try:
            subprocess.run(
                [sys.executable, str(hub_script)],
                capture_output=True, timeout=10,
            )
        except (subprocess.TimeoutExpired, OSError):
            pass  # best-effort


# ── Argument parsing helpers ─────────────────────────────────────────────────

def _parse_since(args: argparse.Namespace) -> datetime | None:
    """Parse --since or --days into a datetime cutoff."""
    if hasattr(args, "since") and args.since:
        try:
            dt = datetime.strptime(args.since, "%Y-%m-%d")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"Invalid date format: {args.since} (use YYYY-MM-DD)", file=sys.stderr)
            sys.exit(1)
    if hasattr(args, "days") and args.days:
        return datetime.now(tz=timezone.utc) - timedelta(days=args.days)
    return None


def _date_range_label(args: argparse.Namespace) -> str:
    """Build a human-readable date range string."""
    if hasattr(args, "since") and args.since:
        return f"since {args.since}"
    if hasattr(args, "days") and args.days:
        return f"last {args.days} days"
    return "all time"


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="transcript-analyser",
        description="Mine Claude Code transcripts for failure signals",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # scan subcommand
    scan_parser = subparsers.add_parser("scan", help="Scan transcripts and output results")
    scan_parser.add_argument("--since", help="Only scan transcripts since YYYY-MM-DD")
    scan_parser.add_argument("--days", type=int, help="Only scan transcripts from last N days")
    scan_parser.add_argument("--format", choices=["json", "markdown"], default="json",
                             help="Output format (default: json)")

    # report subcommand
    report_parser = subparsers.add_parser("report", help="Generate HTML report and open in browser")
    report_parser.add_argument("--since", help="Only scan transcripts since YYYY-MM-DD")
    report_parser.add_argument("--days", type=int, help="Only scan transcripts from last N days")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "report":
        cmd_report(args)


if __name__ == "__main__":
    main()
