#!/bin/bash
# check-file-size.sh - Enforce maximum line count on Python files
# Default limit: 500 lines (excludes tests/ and migrations/)

set -e

MAX_LINES=${MAX_LINES:-500}
FAILED=0

for file in "$@"; do
    if [ ! -f "$file" ]; then
        continue
    fi

    lines=$(wc -l < "$file")
    if [ "$lines" -gt "$MAX_LINES" ]; then
        echo "FAIL: $file has $lines lines (max: $MAX_LINES)"
        FAILED=1
    fi
done

if [ "$FAILED" -eq 1 ]; then
    echo ""
    echo "Refactor files exceeding $MAX_LINES lines before committing."
    exit 1
fi
