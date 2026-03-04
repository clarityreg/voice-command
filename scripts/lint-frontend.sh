#!/bin/bash
# lint-frontend.sh - ESLint wrapper for pre-commit
# Pre-commit passes repo-relative paths (e.g., frontend/src/App.tsx).
# This script strips the frontend/ prefix and runs ESLint from the frontend dir.

set -e

if [ ! -d "frontend" ]; then
    echo "No frontend/ directory found — skipping ESLint."
    exit 0
fi

# Strip frontend/ prefix from each file path
FILES=()
for f in "$@"; do
    FILES+=("${f#frontend/}")
done

if [ ${#FILES[@]} -eq 0 ]; then
    exit 0
fi

cd frontend
npx eslint --no-warn-ignored "${FILES[@]}"
