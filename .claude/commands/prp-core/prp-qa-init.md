---
description: Initialize QA infrastructure — detect project, scaffold directories, generate missing tests, establish baseline
argument-hint: [scope: path or blank for whole project]
---

# QA Initialization

Bootstrap the QA system for this project: detect the stack, scaffold test infrastructure, generate missing tests, and establish a coverage baseline.

## Phase 1: DETECT

Auto-detect the project type, existing test frameworks, and test directories.

### 1.1 Project Type Detection

```bash
# Check for project indicators
[[ -f "package.json" ]] && PROJECT_TYPE="node"
[[ -f "pyproject.toml" || -f "requirements.txt" || -f "setup.py" ]] && PROJECT_TYPE="python"
[[ -f "Cargo.toml" ]] && PROJECT_TYPE="rust"
[[ -f "go.mod" ]] && PROJECT_TYPE="go"
[[ -f "pom.xml" || -f "build.gradle" ]] && PROJECT_TYPE="java"

# Check for monorepo / multi-stack
[[ -d "backend" && -d "frontend" ]] && PROJECT_TYPE="fullstack"
[[ -d "apps" ]] && PROJECT_TYPE="monorepo"
```

### 1.2 Test Framework Detection

```bash
# Node/TypeScript frameworks
grep -q "vitest" package.json 2>/dev/null && TEST_FRAMEWORK="vitest"
grep -q "jest" package.json 2>/dev/null && TEST_FRAMEWORK="jest"
grep -q '"bun"' package.json 2>/dev/null && TEST_FRAMEWORK="bun:test"
grep -q "mocha" package.json 2>/dev/null && TEST_FRAMEWORK="mocha"

# Python frameworks
grep -q "pytest" pyproject.toml 2>/dev/null && TEST_FRAMEWORK="pytest"
grep -q "pytest" requirements.txt 2>/dev/null && TEST_FRAMEWORK="pytest"

# Rust — built-in
[[ -f "Cargo.toml" ]] && TEST_FRAMEWORK="cargo-test"

# Go — built-in
[[ -f "go.mod" ]] && TEST_FRAMEWORK="go-test"
```

### 1.3 Existing Test Directory Detection

```bash
# Scan for existing test directories
find . -maxdepth 4 -type d \( -name "tests" -o -name "test" -o -name "__tests__" -o -name "spec" \) | head -20

# Scan for existing test files
find . -name "test_*" -o -name "*.test.*" -o -name "*.spec.*" -o -name "*_test.go" | head -30
```

### 1.4 Scope

Parse `$ARGUMENTS` for an optional scope path. If provided, restrict all subsequent phases to that directory subtree. If blank, apply to the entire project.

Log detection results:

```
QA Init — Detection Summary
============================
Project type:    {type}
Test framework:  {framework or "NONE DETECTED"}
Test directories: {list or "NONE FOUND"}
Scope:           {scope or "entire project"}
```

---

## Phase 2: SCAFFOLD

Create QA infrastructure that is missing.

### 2.1 QA Artifact Directory

```bash
# Create the QA artifact tree
mkdir -p .claude/PRPs/qa/bugs
mkdir -p .claude/PRPs/qa/reports
```

### 2.2 Test Configuration Files

If no test framework configuration exists, create the appropriate config:

**Vitest** (if `vitest` detected or Node project without framework):
```bash
# Create vitest.config.ts if missing
# Include coverage configuration (v8 or istanbul)
# Set include patterns matching the project structure
```

**Jest** (if `jest` detected):
```bash
# Create jest.config.ts or jest.config.js if missing
# Set testMatch, moduleNameMapper, transform as needed
```

**Bun** (if `bun:test` detected):
```bash
# Bun uses bunfig.toml — add [test] section if missing
```

**Pytest** (if `pytest` detected or Python project without framework):
```bash
# Create conftest.py at project root or tests/ root if missing
# Create pytest.ini or add [tool.pytest] to pyproject.toml if missing
# Include coverage options (pytest-cov)
```

Do NOT overwrite existing configuration. Only create files that are missing.

### 2.3 Test Directories

Create test directories matching the project convention:

- Python: `tests/unit/`, `tests/integration/` (or mirror `backend/apps/` structure)
- Node: `src/__tests__/` or `tests/` depending on convention
- Rust: `tests/` (integration tests directory)
- Go: test files are colocated, no directory needed

### 2.4 Test Scripts in package.json

For Node projects, ensure `package.json` has test scripts:

```json
{
  "scripts": {
    "test": "<framework> run",
    "test:watch": "<framework> --watch",
    "test:coverage": "<framework> run --coverage"
  }
}
```

Only add scripts that are missing. Do NOT overwrite existing scripts.

### 2.5 Test Results CSV

Create the baseline tracking file if it does not exist:

```bash
# Create test-results.csv with header
echo "timestamp,scope,total,passed,failed,skipped,coverage,duration_s" > .claude/PRPs/qa/test-results.csv
```

Only create if the file does not exist.

### 2.6 QA Settings

Check `.claude/prp-settings.json` for a `qa` section. If missing, add default quality gates:

```json
{
  "qa": {
    "quality_gates": {
      "tests_must_pass": true,
      "min_coverage": 80,
      "max_p0_bugs": 0,
      "max_p1_bugs": 3
    },
    "test_framework": "<detected>",
    "test_command": "<detected run command>"
  }
}
```

Log what was created:

```
Scaffold Summary
================
Created: .claude/PRPs/qa/bugs/
Created: .claude/PRPs/qa/reports/
Created: .claude/PRPs/qa/test-results.csv
Updated: .claude/prp-settings.json (added qa section)
{Any config files created}
```

---

## Phase 3: GENERATE

For each source file in scope that does NOT have a corresponding test file, generate tests.

### 3.1 Find Untested Source Files

Build a mapping of source files to their expected test file paths using the detected naming convention. Identify source files with no matching test file.

```bash
# Example for Python
# Source: backend/apps/auth/views.py
# Expected: tests/unit/apps/auth/test_views.py
# Missing? -> add to generation list

# Example for TypeScript
# Source: src/components/Button.tsx
# Expected: src/components/Button.test.tsx  OR  src/__tests__/Button.test.tsx
# Missing? -> add to generation list
```

Exclude from generation:
- Config files, type definitions, barrel/index files
- Files with fewer than 5 lines of logic
- Migration files, generated code
- Files already in test directories

### 3.2 Generate Tests

For each untested file (up to 20 files in a single run), invoke `/prp-test <file>` logic:

1. Read the source file
2. Analyze testable units (functions, classes, methods)
3. Generate a test file following project conventions
4. Write the test file to the correct location

If more than 20 untested files exist, generate for the first 20 (prioritizing files with more exported functions) and note the remainder for a follow-up run.

### 3.3 Log Generation

```
Test Generation Summary
=======================
Source files scanned: {N}
Already tested:       {N}
Tests generated:      {N}
Skipped (too small):  {N}
Remaining (next run): {N}

Generated test files:
  - tests/unit/apps/auth/test_views.py
  - tests/unit/apps/auth/test_models.py
  ...
```

---

## Phase 4: VERIFY

Run all tests to establish a baseline and capture metrics.

### 4.1 Run Tests

Execute the full test suite using the detected framework:

```bash
# Python
pytest tests/ -v --tb=short 2>&1

# Vitest
npx vitest run 2>&1

# Jest
npx jest --verbose 2>&1

# Bun
bun test 2>&1

# Rust
cargo test 2>&1

# Go
go test ./... -v 2>&1
```

Capture:
- Total test count
- Passed count
- Failed count
- Skipped count
- Duration

### 4.2 Run Coverage

Run `/prp-coverage` or the coverage command directly:

```bash
# Python
pytest tests/ --cov=backend --cov-report=term-missing 2>&1

# Vitest
npx vitest run --coverage 2>&1

# Jest
npx jest --coverage 2>&1
```

Capture the overall coverage percentage.

### 4.3 Record Baseline

Append a row to `test-results.csv`:

```
{ISO timestamp},{scope},{total},{passed},{failed},{skipped},{coverage%},{duration_s}
```

### 4.4 Fix Broken Generated Tests

If any newly generated tests fail due to import errors, missing fixtures, or incorrect mocking:
1. Read the error output
2. Fix the test file (correct imports, update mocks, fix assertions)
3. Re-run the failing tests
4. Repeat up to 3 times per file

Tests that fail because they found **real bugs** in source code should be left as-is and reported.

---

## Phase 5: REPORT

Create the initial QA report and present a summary to the user.

### 5.1 Create Initial Report

Save to `.claude/PRPs/qa/reports/{YYYY-MM-DD}-init.md`:

```markdown
# QA Initialization Report

**Date**: {date}
**Project**: {project name from prp-settings or directory name}
**Scope**: {scope or "full project"}

## Detection

| Property | Value |
|----------|-------|
| Project type | {type} |
| Test framework | {framework} |
| Existing test files | {count} |
| Source files | {count} |

## Scaffolding

| Item | Status |
|------|--------|
| QA directories | Created / Already existed |
| Test config | Created / Already existed |
| Test scripts | Added / Already existed |
| Quality gates | Configured / Already existed |

## Test Generation

| Metric | Value |
|--------|-------|
| Source files scanned | {N} |
| Tests generated | {N} |
| Already covered | {N} |
| Skipped | {N} |

## Baseline Metrics

| Metric | Value |
|--------|-------|
| Total tests | {N} |
| Passing | {N} |
| Failing | {N} |
| Skipped | {N} |
| Coverage | {N}% |
| Duration | {N}s |

## Quality Gates

| Gate | Threshold | Current | Status |
|------|-----------|---------|--------|
| Tests pass | all | {pass/fail} | {PASS/FAIL} |
| Coverage | {min}% | {actual}% | {PASS/FAIL} |
| P0 bugs | {max} | 0 | PASS |
| P1 bugs | {max} | 0 | PASS |

## Next Steps

- {List of recommended actions based on results}
- {e.g., "Fix 3 failing tests in tests/unit/auth/"}
- {e.g., "Run `/prp-qa-init` again to cover remaining 12 untested files"}
- {e.g., "Increase coverage from 62% to 80% target"}
```

### 5.2 Output Summary

```
QA Initialization Complete
===========================

Project:    {name} ({type})
Framework:  {framework}
Scope:      {scope}

Scaffolded:
  - QA directories: .claude/PRPs/qa/{bugs,reports}
  - Test config: {files created or "already existed"}
  - Test results CSV initialized

Generated: {N} test files for {N} source files

Baseline:
  Tests:    {passed}/{total} passing ({skipped} skipped)
  Coverage: {coverage}%
  Duration: {duration}s

Quality Gates: {X}/{Y} passing

Report saved: .claude/PRPs/qa/reports/{date}-init.md
HTML report: .claude/PRPs/qa/reports/qa-report.html

{If there are remaining untested files}
Note: {N} source files still need tests. Run `/prp-qa-init` again to continue.

{If there are failing tests}
Warning: {N} tests are failing. Review the failures above and fix before proceeding.
```

### 5.3 Generate HTML Dashboard

After saving the markdown report, generate the HTML QA dashboard:

```bash
uv run scripts/qa-report.py --days 7
```

This produces `.claude/PRPs/qa/reports/qa-report.html` — a dark-themed interactive dashboard with quality gate status, metric cards, test results, coverage trends, and bug tracking.

---

## Output

The primary outputs are:
1. **QA directory structure** scaffolded on disk
2. **Test files** generated for untested source files
3. **Baseline metrics** recorded in `test-results.csv`
4. **Init report** saved to `.claude/PRPs/qa/reports/`
5. **HTML dashboard** generated at `.claude/PRPs/qa/reports/qa-report.html`
6. **Conversational summary** presented to the user
