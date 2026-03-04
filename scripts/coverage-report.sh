#!/bin/bash
# coverage-report.sh - Auto-detects Python/Node, runs tests with coverage,
# saves timestamped reports, and opens HTML report in browser.

set -euo pipefail

REPORT_BASE=".claude/PRPs/coverage"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="$REPORT_BASE/$TIMESTAMP"
LATEST_JSON="$REPORT_BASE/latest.json"

mkdir -p "$REPORT_DIR"

# Temp files to communicate HTML paths out of subshells
_PYTHON_HTML_TMP=$(mktemp)
_NODE_HTML_TMP=$(mktemp)
trap 'rm -f "$_PYTHON_HTML_TMP" "$_NODE_HTML_TMP"' EXIT

# ── Detect project types ──────────────────────────────────────────────────────
HAS_PYTHON=false
HAS_NODE=false

[[ -f "pyproject.toml" || -f "requirements.txt" ]] && HAS_PYTHON=true
[[ -f "package.json" ]] && HAS_NODE=true

if [[ "$HAS_PYTHON" == false && "$HAS_NODE" == false ]]; then
    echo "Error: No supported project type detected (no pyproject.toml, requirements.txt, or package.json)."
    exit 1
fi

# ── Helpers ───────────────────────────────────────────────────────────────────

open_browser() {
    local path="$1"
    if command -v open &>/dev/null; then
        open "$path"
    elif command -v xdg-open &>/dev/null; then
        xdg-open "$path"
    else
        echo "  Open manually: $path"
    fi
}

# ── Python coverage ───────────────────────────────────────────────────────────

run_python_coverage() {
    echo ""
    echo "=== Python Coverage ==="

    local pytest_cmd="pytest"
    if command -v poetry &>/dev/null && [[ -f "pyproject.toml" ]]; then
        pytest_cmd="poetry run pytest"
    fi

    # Determine test directory
    local test_dir="tests"
    [[ -d "backend/tests" ]] && test_dir="backend/tests"
    [[ -d "tests" ]] && test_dir="tests"

    # Determine source directory for coverage
    local cov_src="."
    [[ -d "backend" ]] && cov_src="backend"
    [[ -d "src" ]] && cov_src="src"

    # Run pytest with coverage
    PYTHONPATH="${cov_src}" $pytest_cmd "$test_dir" \
        --cov="$cov_src" \
        --cov-report=html:htmlcov \
        --cov-report=json:coverage.json \
        --cov-report=term-missing:skip-covered \
        -q 2>&1 || {
        echo "Warning: pytest exited with errors — coverage data may be partial."
    }

    # Extract overall coverage from JSON
    local overall=0
    if [[ -f "coverage.json" ]]; then
        overall=$(python3 -c "
import json
try:
    data = json.load(open('coverage.json'))
    pct = data.get('totals', {}).get('percent_covered', 0)
    print(f'{pct:.1f}')
except Exception:
    print('0')
")
    fi

    # Copy reports to timestamped dir
    if [[ -d "htmlcov" ]]; then
        cp -r htmlcov "$REPORT_DIR/python-html"
        echo "$REPORT_DIR/python-html/index.html" > "$_PYTHON_HTML_TMP"
        echo "  HTML report: $REPORT_DIR/python-html/index.html"
    fi
    [[ -f "coverage.json" ]] && cp coverage.json "$REPORT_DIR/python-coverage.json"

    echo "  Overall coverage: ${overall}%"
    echo "$overall"
}

# ── Node/Vitest coverage ──────────────────────────────────────────────────────

run_node_coverage() {
    echo ""
    echo "=== Node/Vitest Coverage ==="

    local pkg_manager="npm"
    command -v pnpm &>/dev/null && [[ -f "pnpm-lock.yaml" ]] && pkg_manager="pnpm"
    command -v yarn &>/dev/null && [[ -f "yarn.lock" ]] && pkg_manager="yarn"

    local cov_dir="coverage"
    [[ -d "frontend" ]] && cov_dir="frontend/coverage"

    # Run vitest coverage with json-summary reporter for metrics extraction
    local cov_args="--coverage --coverage.reporter=text --coverage.reporter=html --coverage.reporter=json-summary"
    if [[ -d "frontend" ]]; then
        cd frontend
        npx vitest run $cov_args 2>&1 || {
            echo "Warning: vitest exited with errors — coverage data may be partial."
        }
        cd ..
    else
        npx vitest run $cov_args 2>&1 || {
            echo "Warning: vitest exited with errors — coverage data may be partial."
        }
    fi

    # Extract overall coverage from json-summary or coverage-final.json
    local overall=0
    local json_path="$cov_dir/coverage-summary.json"
    if [[ -f "$json_path" ]]; then
        overall=$(python3 -c "
import json
try:
    data = json.load(open('$json_path'))
    total = data.get('total', {})
    lines = total.get('lines', {}).get('pct', 0)
    print(f'{lines:.1f}')
except Exception:
    print('0')
")
    elif [[ -f "$cov_dir/coverage-final.json" ]]; then
        # Fallback: parse istanbul-style coverage-final.json
        overall=$(python3 -c "
import json
try:
    data = json.load(open('$cov_dir/coverage-final.json'))
    total_stmts = total_covered = 0
    for f in data.values():
        s = f.get('s', {})
        total_stmts += len(s)
        total_covered += sum(1 for v in s.values() if v > 0)
    pct = (total_covered / total_stmts * 100) if total_stmts else 0
    print(f'{pct:.1f}')
except Exception:
    print('0')
")
    fi

    # Copy reports
    if [[ -d "$cov_dir" ]]; then
        local html_index="$cov_dir/index.html"
        [[ ! -f "$html_index" ]] && html_index=$(find "$cov_dir" -name "index.html" 2>/dev/null | head -1)
        if [[ -n "$html_index" && -f "$html_index" ]]; then
            cp -r "$cov_dir" "$REPORT_DIR/node-html"
            echo "$REPORT_DIR/node-html/index.html" > "$_NODE_HTML_TMP"
            echo "  HTML report: $REPORT_DIR/node-html/index.html"
        fi
    fi

    echo "  Overall coverage: ${overall}%"
    echo "$overall"
}

# ── Run coverage ──────────────────────────────────────────────────────────────

PYTHON_COVERAGE=0
NODE_COVERAGE=0

if [[ "$HAS_PYTHON" == true ]]; then
    PYTHON_COVERAGE=$(run_python_coverage | tail -1)
fi

if [[ "$HAS_NODE" == true ]]; then
    NODE_COVERAGE=$(run_node_coverage | tail -1)
fi

# ── Compute overall ───────────────────────────────────────────────────────────

OVERALL_COVERAGE=$(python3 -c "
py = float('${PYTHON_COVERAGE}' or 0)
node = float('${NODE_COVERAGE}' or 0)
has_py = '${HAS_PYTHON}' == 'true'
has_node = '${HAS_NODE}' == 'true'
if has_py and has_node:
    print(f'{(py + node) / 2:.1f}')
elif has_py:
    print(f'{py:.1f}')
else:
    print(f'{node:.1f}')
")

# ── Write latest.json ─────────────────────────────────────────────────────────

PROJECT_TYPE="unknown"
if [[ "$HAS_PYTHON" == true && "$HAS_NODE" == true ]]; then
    PROJECT_TYPE="fullstack"
elif [[ "$HAS_PYTHON" == true ]]; then
    PROJECT_TYPE="python"
else
    PROJECT_TYPE="node"
fi

REPORT_HTML_PATH=""
PYTHON_HTML_SRC=$(cat "$_PYTHON_HTML_TMP" 2>/dev/null || true)
NODE_HTML_SRC=$(cat "$_NODE_HTML_TMP" 2>/dev/null || true)
[[ -n "$PYTHON_HTML_SRC" ]] && REPORT_HTML_PATH="$PYTHON_HTML_SRC"
[[ -n "$NODE_HTML_SRC" ]] && REPORT_HTML_PATH="$NODE_HTML_SRC"

python3 -c "
import json, os
data = {
    'timestamp': '$(date -u +"%Y-%m-%dT%H:%M:%SZ")',
    'type': '$PROJECT_TYPE',
    'overall_coverage': float('$OVERALL_COVERAGE'),
    'python_coverage': float('$PYTHON_COVERAGE') if '$HAS_PYTHON' == 'true' else None,
    'node_coverage': float('$NODE_COVERAGE') if '$HAS_NODE' == 'true' else None,
    'report_path': '$REPORT_DIR',
    'html_report': '$REPORT_HTML_PATH',
}
os.makedirs('$REPORT_BASE', exist_ok=True)
with open('$LATEST_JSON', 'w') as f:
    json.dump(data, f, indent=2)
print(json.dumps(data, indent=2))
"

echo ""
echo "=========================================="
echo "Coverage Report"
echo "=========================================="
echo "  Overall:  ${OVERALL_COVERAGE}%"
echo "  Saved to: $REPORT_DIR"
echo "  Latest:   $LATEST_JSON"
echo "=========================================="

# ── Check against targets ─────────────────────────────────────────────────────

python3 -c "
import json, sys
try:
    settings = json.load(open('.claude/prp-settings.json'))
    targets = settings.get('coverage', {}).get('targets', {})
    overall_target = targets.get('overall', 80)
    actual = float('$OVERALL_COVERAGE')
    if actual < overall_target:
        print(f'Warning: Coverage {actual}% is below target {overall_target}%')
        sys.exit(1)
    else:
        print(f'Coverage target met: {actual}% >= {overall_target}%')
except FileNotFoundError:
    pass
except SystemExit as e:
    sys.exit(e.code)
" || true

# ── Open HTML report ──────────────────────────────────────────────────────────

if [[ -n "$REPORT_HTML_PATH" && -f "$REPORT_HTML_PATH" ]]; then
    echo ""
    echo "Opening coverage report..."
    open_browser "$REPORT_HTML_PATH"
fi
