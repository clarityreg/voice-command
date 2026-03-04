#!/usr/bin/env bash
# QA Gate Check — Pre-commit hook
# Skippable: SKIP=qa-gate-check git commit -m "msg"

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SETTINGS_FILE="$PROJECT_ROOT/.claude/prp-settings.json"
CSV_FILE="$PROJECT_ROOT/.claude/PRPs/qa/test-results.csv"

# Check if settings exist
if [ ! -f "$SETTINGS_FILE" ]; then
  echo "⚠️  No prp-settings.json found, skipping QA gate check"
  exit 0
fi

# Check if CSV exists (no test history = skip)
if [ ! -f "$CSV_FILE" ]; then
  echo "⚠️  No test results found. Run tests first with /prp-qa-gate"
  exit 0
fi

# Check if last test run was recent (within 30 minutes)
LAST_TIMESTAMP=$(tail -1 "$CSV_FILE" | cut -d',' -f1)
NOW=$(date +%s)
AGE=$((NOW - LAST_TIMESTAMP))

if [ $AGE -gt 1800 ]; then
  echo "⚠️  Last test run was $(($AGE / 60)) minutes ago. Consider re-running tests."
  # Don't block — just warn about stale results
  exit 0
fi

# Run gate check via Python script
python3 "$SCRIPT_DIR/qa-metrics.py" gates
