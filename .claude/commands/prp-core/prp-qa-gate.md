---
description: Run quality gate checks — verify tests, coverage, and bug thresholds before merge or release
argument-hint: [--strict | --advisory]
---

# Quality Gate Check

Evaluate the project against configured quality gates. Determines whether the project meets the minimum bar for merge, deployment, or release.

## Phase 1: CHECK

Gather current quality data from test runs, coverage reports, and the bug tracker.

### 1.1 Parse Arguments

Parse `$ARGUMENTS` for mode:
- `--strict` — All gates must pass. Exit with failure status if any gate fails. This is the default if no argument is provided.
- `--advisory` — Report results only. No failure status regardless of gate outcomes.

### 1.2 Run Tests (or Use Recent Results)

Check if tests were run recently enough to skip a re-run:

```bash
# Read the last row of test-results.csv
LAST_RUN=$(tail -1 .claude/PRPs/qa/test-results.csv 2>/dev/null)

# Parse the timestamp from the last row
# If the timestamp is within the last 10 minutes, use cached results
# Otherwise, re-run the test suite
```

If re-running tests is needed, execute the project's test command:

```bash
# Detect test command from prp-settings.json qa.test_command
# Or fall back to framework detection:

# Python
pytest tests/ -v --tb=short 2>&1

# Node (vitest)
npx vitest run 2>&1

# Node (jest)
npx jest --verbose 2>&1

# Node (bun)
bun test 2>&1

# Rust
cargo test 2>&1

# Go
go test ./... -v 2>&1
```

Capture: total tests, passed, failed, skipped, duration.

### 1.3 Get Coverage Data

Run coverage or read from cached results:

```bash
# Check for recent coverage in .claude/PRPs/coverage/latest.json
# If stale (>10 min), re-run /prp-coverage

# Python
pytest tests/ --cov=backend --cov-report=term-missing --cov-report=json 2>&1

# Vitest
npx vitest run --coverage 2>&1

# Jest
npx jest --coverage 2>&1
```

Extract the overall coverage percentage.

### 1.4 Scan Open Bugs

```bash
# Count open bugs by severity from .claude/PRPs/qa/bugs/
# A bug file is "open" if it contains "Status: OPEN" (case-insensitive)
# Parse severity from the "Severity: P0" line

P0_COUNT=0
P1_COUNT=0
P2_COUNT=0
P3_COUNT=0
P4_COUNT=0

for bug_file in .claude/PRPs/qa/bugs/BUG-*.md; do
  if grep -qi "Status:.*OPEN" "$bug_file" 2>/dev/null; then
    severity=$(grep -oi "Severity:.*P[0-4]" "$bug_file" | grep -o "P[0-4]")
    case "$severity" in
      P0) P0_COUNT=$((P0_COUNT + 1)) ;;
      P1) P1_COUNT=$((P1_COUNT + 1)) ;;
      P2) P2_COUNT=$((P2_COUNT + 1)) ;;
      P3) P3_COUNT=$((P3_COUNT + 1)) ;;
      P4) P4_COUNT=$((P4_COUNT + 1)) ;;
    esac
  fi
done
```

### 1.5 Load Quality Gate Thresholds

Read from `.claude/prp-settings.json`:

```json
{
  "qa": {
    "quality_gates": {
      "tests_must_pass": true,
      "min_coverage": 80,
      "max_p0_bugs": 0,
      "max_p1_bugs": 3
    }
  }
}
```

If no `qa.quality_gates` section exists, use defaults:
- `tests_must_pass`: true
- `min_coverage`: 80
- `max_p0_bugs`: 0
- `max_p1_bugs`: 3

---

## Phase 2: EVALUATE

Check each quality gate against the collected data.

### 2.1 Gate: Tests Must Pass

```
Gate:      tests_must_pass
Threshold: All tests pass (0 failures)
Actual:    {failed_count} failures out of {total_count} tests
Verdict:   {PASS if failed_count == 0, else FAIL}
```

If failing:
- List the names of failing tests (up to 10)
- Suggest: "Run `pytest <file> -v` or `npx vitest run <file>` to debug failures"

### 2.2 Gate: Minimum Coverage

```
Gate:      min_coverage
Threshold: {min_coverage}%
Actual:    {actual_coverage}%
Verdict:   {PASS if actual >= threshold, else FAIL}
Delta:     {actual - threshold}% {above/below} threshold
```

If failing:
- List the 5 files with lowest coverage
- Suggest: "Run `/prp-test <file>` on low-coverage files to improve"

### 2.3 Gate: Maximum P0 Bugs

```
Gate:      max_p0_bugs
Threshold: {max_p0_bugs} maximum open P0 bugs
Actual:    {p0_count} open P0 bugs
Verdict:   {PASS if p0_count <= threshold, else FAIL}
```

If failing:
- List the open P0 bug filenames and titles
- Suggest: "P0 bugs must be resolved before release. Review `.claude/PRPs/qa/bugs/` for details"

### 2.4 Gate: Maximum P1 Bugs

```
Gate:      max_p1_bugs
Threshold: {max_p1_bugs} maximum open P1 bugs
Actual:    {p1_count} open P1 bugs
Verdict:   {PASS if p1_count <= threshold, else FAIL}
```

If failing:
- List the open P1 bug filenames and titles
- Suggest: "Address P1 bugs or demote if severity was overestimated"

### 2.5 Overall Verdict

```
OVERALL: {PASS if all gates pass, else FAIL}
```

In `--strict` mode, a FAIL verdict means the quality bar is not met.
In `--advisory` mode, FAIL is reported but does not block.

---

## Phase 3: REPORT

Present results clearly to the user.

### 3.1 Gate Results Table

```
Quality Gate Report
====================

Mode: {strict | advisory}
Date: {ISO date}

| Gate | Threshold | Actual | Status |
|------|-----------|--------|--------|
| Tests pass | 0 failures | {N} failures | {PASS/FAIL} |
| Coverage | >= {N}% | {N}% | {PASS/FAIL} |
| P0 bugs | <= {N} | {N} open | {PASS/FAIL} |
| P1 bugs | <= {N} | {N} open | {PASS/FAIL} |

Overall: {PASS / FAIL}
```

### 3.2 Details for Failing Gates

For each failing gate, include a details section:

```
--- Failing Gate: Tests Must Pass ---

{N} tests are failing:
  1. test_auth_login_expired_token (tests/unit/test_auth.py)
  2. test_payment_refund_idempotency (tests/unit/test_payments.py)
  ...

Suggested action: Fix failing tests before merging.
  Run: pytest tests/unit/test_auth.py -v -k "expired_token"
```

```
--- Failing Gate: Minimum Coverage ---

Current coverage: {N}% (need {threshold}%)
Gap: {delta}%

Lowest-coverage files:
  1. backend/apps/auth/views.py — 42%
  2. backend/apps/payments/webhooks.py — 51%
  ...

Suggested action: Generate tests for low-coverage files.
  Run: /prp-test backend/apps/auth/views.py
```

```
--- Failing Gate: P0 Bugs ---

{N} open P0 bugs:
  1. BUG-security-001.md — "SQL injection in search endpoint"
  2. BUG-data-003.md — "Data loss on concurrent writes"

Suggested action: P0 bugs are release blockers. Resolve immediately.
```

### 3.3 Passing Summary (when all gates pass)

```
All quality gates PASSED.

  Tests:    {passed}/{total} passing (0 failures)
  Coverage: {coverage}% (threshold: {min}%)
  P0 bugs:  {count} open (max: {max})
  P1 bugs:  {count} open (max: {max})

The project meets the quality bar for merge/release.
```

### 3.4 Append to Test Results CSV

Record this gate check in the tracking file:

```
{ISO timestamp},{scope},{total},{passed},{failed},{skipped},{coverage},{duration_s}
```

---

## Output

The output is conversational. The gate report is presented directly to the user. No artifact file is saved unless the user explicitly requests it.

Key behaviors:
- In `--strict` mode: clearly communicate PASS or FAIL. If FAIL, list every failing gate with actionable remediation steps.
- In `--advisory` mode: present the same information but frame it as informational ("X gates would fail if enforced").
- Always suggest specific next actions for any failing gate.
- If `.claude/PRPs/qa/` does not exist, suggest running `/prp-qa-init` first.
