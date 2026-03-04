---
name: checking-qa-gates
description: "When the user runs /prp-commit or /prp-pr, checks whether QA quality gates are satisfied (tests passing, coverage threshold, open P0/P1 bugs). Advisory only — warns but never blocks."
---

# QA Gate Nudge

When the user is about to commit or create a PR, check whether QA quality gates are satisfied. If any gate is failing, advise the user before they proceed.

## When to trigger

Activate when the user invokes either of these commands:

- `/prp-commit` (i.e., the prp-commit skill/command is referenced)
- `/prp-pr` (i.e., the prp-pr skill/command is referenced)

Do NOT trigger on:

- Normal file edits, reads, or searches
- `/prp-validate`, `/prp-test`, or other non-commit commands
- If the gate check has already been shown once in this session

## How to check QA gates

1. **Check for test results CSV** at `.claude/PRPs/qa/test-results.csv`
   - If the file does not exist, warn: "No test results found. Consider running tests before committing."
   - If the file exists, read the **last row** (most recent result).

2. **Check test pass status** from the last row:
   - Parse the `failed` column. If `failed > 0`, the gate fails.

3. **Check coverage threshold**:
   - Read `.claude/prp-settings.json` and get `qa.quality_gates.min_coverage` (default: 80).
   - Parse `coverage_pct` from the last CSV row. If below the threshold, the gate fails.

4. **Check for open P0/P1 bugs**:
   - Look in `.claude/PRPs/qa/bugs/` for files starting with `P0-` or `P1-`.
   - Read `qa.quality_gates.max_p0_bugs` (default: 0) and `qa.quality_gates.max_p1_bugs` (default: 2).
   - If the count of P0 files exceeds max_p0_bugs, the gate fails.
   - If the count of P1 files exceeds max_p1_bugs, the gate fails.

## What to say

### No test results found

> No QA test results found at `.claude/PRPs/qa/test-results.csv`. Consider running tests before committing. You can use `/prp-qa-gate` to run tests and record results.

### One or more gates failing

> **QA Gate Warning:** Some quality gates are not passing:
> - [List each failing gate with current value vs threshold]
>
> Consider running `/prp-qa-gate` to resolve these before committing.

### All gates passing

Say nothing — do not interrupt the user if everything looks good.

## Rules

- **Never block** — this is advisory only. Present the warning and continue with the commit/PR flow.
- **Once per session** — do not repeat the nudge if the user has already seen it in this session, even if they run `/prp-commit` or `/prp-pr` again.
- **Be brief** — keep the warning to a few lines. Do not explain why QA gates matter.
- **Do not auto-run** tests or `/prp-qa-gate` — only suggest it. The user decides.
