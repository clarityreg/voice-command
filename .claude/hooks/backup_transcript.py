#!/usr/bin/env python3
"""
Transcript Backup (PreCompact)
==============================
Before compaction fires, saves the event data (which includes the
conversation transcript) to .claude/transcripts/{ISO-timestamp}.json.
Best-effort — never blocks compaction.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

TRANSCRIPTS_DIR = Path(__file__).resolve().parents[1] / "transcripts"


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    try:
        TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_path = TRANSCRIPTS_DIR / f"{timestamp}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # Best-effort — never block compaction

    sys.exit(0)


if __name__ == "__main__":
    main()
