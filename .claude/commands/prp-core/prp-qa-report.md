---
description: Generate a QA report with test results, coverage trends, bug tracker summary, and quality gate status
argument-hint: <daily|weekly|release|--days N>
---

# QA Report

Generate a comprehensive QA report covering test results, coverage trends, bug status, and quality gate compliance.

## Phase 1: COLLECT

Gather all available QA data from the project.

### 1.1 Parse Arguments

Parse `$ARGUMENTS` for report type:
- `daily` — Cover the last 24 hours of data (default if no argument)
- `weekly` — Cover the last 7 days
- `release` — Cover all data since the last git tag (or all data if no tags)
- `--days N` — Cover the last N days

```bash
# Determine date range
case "$REPORT_TYPE" in
  daily)   SINCE=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "1 day ago" +%Y-%m-%d) ;;
  weekly)  SINCE=$(date -v-7d +%Y-%m-%d 2>/dev/null || date -d "7 days ago" +%Y-%m-%d) ;;
  release) SINCE=$(git describe --tags --abbrev=0 2>/dev/null | xargs git log -1 --format=%ci | cut -d' ' -f1) ;;
  *)       SINCE=$(date -v-${DAYS}d +%Y-%m-%d 2>/dev/null || date -d "${DAYS} days ago" +%Y-%m-%d) ;;
esac
```

### 1.2 Read Test Results

Parse `.claude/PRPs/qa/test-results.csv` for rows within the date range:

```
timestamp,scope,total,passed,failed,skipped,coverage,duration_s
```

Collect:
- All rows where `timestamp >= SINCE`
- Most recent row (for current state)
- Earliest row in range (for trend comparison)

If no test-results.csv exists, note "No historical test data available" and suggest running `/prp-qa-init`.

### 1.3 Read Coverage Data

Check for coverage data:
1. Latest entry in `test-results.csv` (coverage column)
2. `.claude/PRPs/coverage/latest.json` (if exists)
3. Coverage entries within the date range for trend analysis

### 1.4 Scan Bug Tracker

Read all bug files in `.claude/PRPs/qa/bugs/`:

```bash
# For each BUG-*.md file, extract:
# - Severity (P0-P4)
# - Category (security, performance, etc.)
# - Status (OPEN, CLOSED, IN_PROGRESS)
# - Filed date
# - Resolved date (if closed)
```

Classify bugs into:
- **Open** bugs by severity
- **Closed** bugs within the date range (resolved during this period)
- **New** bugs within the date range (filed during this period)

### 1.5 Count Lines of Code

```bash
# Get LOC count for defect density calculation
# Use cloc, tokei, or wc -l as fallback

# Preferred: cloc (if installed)
cloc --json --quiet . 2>/dev/null

# Fallback: count non-blank, non-comment lines
find . -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.rs" -o -name "*.go" | \
  grep -v node_modules | grep -v __pycache__ | grep -v .git | \
  xargs wc -l 2>/dev/null | tail -1
```

---

## Phase 2: CALCULATE

Derive metrics from the collected data.

### 2.1 Test Pass Rate

```
pass_rate = (total_passed / total_tests) * 100

# Over the date range: aggregate all runs
total_passed_sum = sum of passed across all runs in range
total_tests_sum  = sum of total across all runs in range
aggregate_pass_rate = (total_passed_sum / total_tests_sum) * 100
```

### 2.2 Coverage Trend

```
# Compare first and last coverage values in the date range
coverage_start = earliest coverage value in range
coverage_end   = most recent coverage value
coverage_delta = coverage_end - coverage_start
coverage_trend = "improving" if delta > 0, "declining" if delta < 0, "stable" if delta == 0
```

### 2.3 Defect Density

```
defect_density = (total_open_bugs / (total_loc / 1000))
# Expressed as: bugs per 1,000 lines of code
```

Industry benchmarks for context:
- < 1.0: Excellent
- 1.0 - 5.0: Good
- 5.0 - 10.0: Needs attention
- > 10.0: Critical

### 2.4 Mean Time to Resolve (MTTR)

```
# For each closed bug in the date range:
resolution_time = resolved_date - filed_date (in days)

mttr = average(resolution_times) if any closed bugs, else "N/A"
```

### 2.5 Bug Counts by Severity

```
open_bugs = { P0: N, P1: N, P2: N, P3: N, P4: N }
new_bugs  = { P0: N, P1: N, P2: N, P3: N, P4: N }  # filed in range
closed_bugs = { P0: N, P1: N, P2: N, P3: N, P4: N }  # resolved in range
```

### 2.6 Quality Gates

Evaluate current state against quality gates from `.claude/prp-settings.json` (same logic as `/prp-qa-gate`).

---

## Phase 3: FORMAT

Generate a markdown report.

### 3.1 Report Content

```markdown
# QA Report — {type}

**Period**: {start_date} to {end_date}
**Generated**: {YYYY-MM-DD HH:MM}
**Project**: {project name}
**Branch**: {current branch}

---

## Executive Summary

**Overall Status**: {PASS / FAIL / AT RISK}

{1-3 sentence summary of project health. Examples:}
{- "All quality gates pass. The project is in good health with 94% test pass rate and 83% coverage."}
{- "FAILING: 2 P0 bugs are open and coverage has dropped below the 80% threshold."}
{- "AT RISK: Test pass rate is declining (98% -> 91%) and 3 new P1 bugs were filed this week."}

**Key Metrics**:
| Metric | Value | Trend |
|--------|-------|-------|
| Test pass rate | {N}% | {up/down/stable arrow} |
| Coverage | {N}% | {up/down/stable arrow} |
| Open bugs | {N} ({P0}: {N}, {P1}: {N}) | {+/-N from last period} |
| Defect density | {N}/kLOC | {assessment} |
| MTTR | {N} days | {up/down/stable arrow} |

---

## Test Results

### Recent Runs

| Timestamp | Scope | Total | Passed | Failed | Skipped | Coverage | Duration |
|-----------|-------|-------|--------|--------|---------|----------|----------|
{rows from test-results.csv within the date range, most recent first, max 20 rows}

### Summary

- **Total runs in period**: {N}
- **Aggregate pass rate**: {N}% ({passed}/{total} across all runs)
- **Average duration**: {N}s
- **Flaky tests**: {list any tests that flip between pass/fail across runs, or "none detected"}

---

## Coverage Analysis

### Current Coverage: {N}%

**Target**: {min_coverage from quality gates}%
**Status**: {ABOVE/BELOW target by N%}

### Trend

| Date | Coverage | Delta |
|------|----------|-------|
{coverage values from test-results.csv, showing progression}

{If coverage is declining:}
**Warning**: Coverage has declined by {N}% over this period. Lowest-coverage areas should be prioritized for test generation.

{If coverage is improving:}
Coverage has improved by {N}% over this period.

---

## Bug Tracker

### Open Bugs by Severity

| Severity | Count | Bugs |
|----------|-------|------|
| P0 (Critical) | {N} | {list of bug IDs/titles} |
| P1 (High) | {N} | {list of bug IDs/titles} |
| P2 (Medium) | {N} | {list of bug IDs/titles} |
| P3 (Low) | {N} | {list of bug IDs/titles} |
| P4 (Enhancement) | {N} | {list of bug IDs/titles} |
| **Total** | **{N}** | |

### Activity This Period

| Metric | Count |
|--------|-------|
| New bugs filed | {N} |
| Bugs resolved | {N} |
| Net change | {+/-N} |

### Bugs by Category

| Category | Open | Closed (period) | New (period) |
|----------|------|-----------------|--------------|
| security | {N} | {N} | {N} |
| performance | {N} | {N} | {N} |
| functionality | {N} | {N} | {N} |
| ui | {N} | {N} | {N} |
| data | {N} | {N} | {N} |
| integration | {N} | {N} | {N} |

### Defect Density

**{N} bugs per 1,000 lines of code** — {assessment: Excellent / Good / Needs attention / Critical}

### Mean Time to Resolve

**{N} days** (based on {N} bugs resolved in this period)

{If no bugs were resolved: "No bugs were resolved in this period."}

---

## Quality Gates Status

| Gate | Threshold | Current | Status |
|------|-----------|---------|--------|
| Tests pass | 0 failures | {N} failures | {PASS/FAIL} |
| Coverage | >= {N}% | {N}% | {PASS/FAIL} |
| P0 bugs | <= {N} | {N} open | {PASS/FAIL} |
| P1 bugs | <= {N} | {N} open | {PASS/FAIL} |

**Overall**: {PASS / FAIL}

{If any gates fail, list which ones and why}

---

## Recommendations

{Generate 3-5 actionable recommendations based on the data. Examples:}

1. **{recommendation title}** — {description}
   - Action: {specific command or step}

2. **{recommendation title}** — {description}
   - Action: {specific command or step}

{Examples of recommendations:}
{- "Increase coverage for backend/apps/auth/ (currently 42%) — Run `/prp-test backend/apps/auth/views.py`"}
{- "Resolve P0 bug BUG-security-001 before release — This is a release blocker"}
{- "Investigate flaky test test_concurrent_writes — Failed in 3 of 8 runs this week"}
{- "Coverage trend is negative (-4% this week) — Prioritize test generation for new code"}
{- "Consider adding integration tests — All 12 bugs this period were integration-layer issues"}
```

---

## Phase 4: SAVE

### 4.1 Ensure Directory Exists

```bash
mkdir -p .claude/PRPs/qa/reports
```

### 4.2 Save Report

Save to `.claude/PRPs/qa/reports/{YYYY-MM-DD}-{type}.md`:

Examples:
- `.claude/PRPs/qa/reports/2026-02-28-daily.md`
- `.claude/PRPs/qa/reports/2026-02-28-weekly.md`
- `.claude/PRPs/qa/reports/2026-02-28-release.md`

If a report with the same name already exists (e.g., two daily reports on the same day), append a sequence number:
- `.claude/PRPs/qa/reports/2026-02-28-daily-2.md`

### 4.3 Confirm

```
Report saved: .claude/PRPs/qa/reports/{filename}
```

---

## Output

Present a condensed summary to the user after saving:

```
QA Report — {type}
===================

Period:   {start} to {end}
Status:   {PASS / FAIL / AT RISK}

Tests:    {passed}/{total} ({pass_rate}%) | Coverage: {N}%
Bugs:     {open_total} open ({P0}: {N}, {P1}: {N}) | {new} new, {closed} resolved
Density:  {N}/kLOC | MTTR: {N} days
Gates:    {X}/{Y} passing

{If any gates fail:}
Failing gates:
  - {gate name}: {current} vs threshold {threshold}

Report: .claude/PRPs/qa/reports/{filename}
```

If `.claude/PRPs/qa/` does not exist or has no data, suggest running `/prp-qa-init` first.

The primary output is the **report file saved to disk**. The summary is conversational.

---

## Phase 5: HTML

After saving the markdown report, generate the HTML QA dashboard:

```bash
uv run scripts/qa-report.py --days {same days value used above}
```

This produces `.claude/PRPs/qa/reports/qa-report.html` — an interactive dark-themed dashboard with quality gate status, metric cards, test result history, coverage trend, and bug tracker visualization. The report is also discoverable via the PRP reports hub (`uv run scripts/reports-hub.py`).

```
HTML dashboard: .claude/PRPs/qa/reports/qa-report.html
```
