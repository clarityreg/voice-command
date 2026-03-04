#!/bin/bash
# Auto-format hook - runs after Write/Edit operations
# Detects file type and runs appropriate formatter

FILE_PATH="$1"

# Exit if no file path provided
[[ -z "$FILE_PATH" ]] && exit 0

# Exit if file doesn't exist
[[ ! -f "$FILE_PATH" ]] && exit 0

# Get file extension
EXT="${FILE_PATH##*.}"

# Get project root (where the script is called from)
PROJECT_ROOT="$(pwd)"

# Determine formatter based on file extension and available tools
case "$EXT" in
  # TypeScript/JavaScript
  ts|tsx|js|jsx|mjs|cjs)
    if [[ -f "$PROJECT_ROOT/node_modules/.bin/prettier" ]]; then
      npx prettier --write "$FILE_PATH" 2>/dev/null
    elif [[ -f "$PROJECT_ROOT/node_modules/.bin/eslint" ]]; then
      npx eslint --fix "$FILE_PATH" 2>/dev/null
    elif command -v prettier &>/dev/null; then
      prettier --write "$FILE_PATH" 2>/dev/null
    fi
    ;;

  # Python
  py)
    if command -v black &>/dev/null; then
      black --quiet "$FILE_PATH" 2>/dev/null
    elif command -v autopep8 &>/dev/null; then
      autopep8 --in-place "$FILE_PATH" 2>/dev/null
    fi
    # Also run isort if available
    if command -v isort &>/dev/null; then
      isort --quiet "$FILE_PATH" 2>/dev/null
    fi
    ;;

  # Rust
  rs)
    if command -v rustfmt &>/dev/null; then
      rustfmt "$FILE_PATH" 2>/dev/null
    fi
    ;;

  # Go
  go)
    if command -v gofmt &>/dev/null; then
      gofmt -w "$FILE_PATH" 2>/dev/null
    fi
    ;;

  # JSON
  json)
    if command -v jq &>/dev/null; then
      tmp=$(mktemp)
      jq '.' "$FILE_PATH" > "$tmp" 2>/dev/null && mv "$tmp" "$FILE_PATH"
    elif [[ -f "$PROJECT_ROOT/node_modules/.bin/prettier" ]]; then
      npx prettier --write "$FILE_PATH" 2>/dev/null
    fi
    ;;

  # YAML
  yaml|yml)
    if [[ -f "$PROJECT_ROOT/node_modules/.bin/prettier" ]]; then
      npx prettier --write "$FILE_PATH" 2>/dev/null
    fi
    ;;

  # Markdown
  md)
    if [[ -f "$PROJECT_ROOT/node_modules/.bin/prettier" ]]; then
      npx prettier --write "$FILE_PATH" 2>/dev/null
    fi
    ;;

  # CSS/SCSS/LESS
  css|scss|less)
    if [[ -f "$PROJECT_ROOT/node_modules/.bin/prettier" ]]; then
      npx prettier --write "$FILE_PATH" 2>/dev/null
    fi
    ;;

  # HTML
  html|htm)
    if [[ -f "$PROJECT_ROOT/node_modules/.bin/prettier" ]]; then
      npx prettier --write "$FILE_PATH" 2>/dev/null
    fi
    ;;
esac

# Always exit successfully - formatting is best-effort
exit 0
