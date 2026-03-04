---
description: File a structured bug report with severity classification, root cause analysis, and optional issue tracker linking
argument-hint: <bug description>
---

# Bug Report

Create a structured, classified bug report and save it to the QA bug tracker. Optionally link to Plane or GitHub Issues.

## Phase 1: CLASSIFY

Parse `$ARGUMENTS` for the bug description. Analyze the description to determine severity and category.

### 1.1 Severity Classification

Assign a severity level based on the description and any investigation you can do:

| Severity | Criteria | Examples |
|----------|----------|----------|
| **P0** | System down, data loss, security vulnerability | Crash on startup, SQL injection, user data exposed, database corruption |
| **P1** | Core feature broken, no workaround | Login fails for all users, payments not processing, API returns 500 on primary endpoint |
| **P2** | Feature degraded, workaround exists | Search returns wrong order, export takes 10x longer than expected, error message is misleading |
| **P3** | Minor issue, cosmetic | Typo in UI, misaligned button, wrong color on hover state |
| **P4** | Enhancement request | "Would be nice if...", performance optimization idea, UX improvement suggestion |

If severity is ambiguous, lean one level higher (more severe) and note the uncertainty.

### 1.2 Category Classification

Assign a category:

| Category | Scope |
|----------|-------|
| `security` | Authentication, authorization, injection, data exposure, CSRF, XSS |
| `performance` | Slow queries, memory leaks, high CPU, timeouts, N+1 queries |
| `functionality` | Feature does not work as specified, logic errors, incorrect output |
| `ui` | Layout, styling, responsiveness, accessibility, rendering issues |
| `data` | Data integrity, migrations, corruption, incorrect calculations |
| `integration` | Third-party APIs, webhooks, message queues, external services |

### 1.3 Auto-Investigation

Before documenting, attempt a quick investigation:

1. **Search the codebase** for keywords from the bug description
2. **Check recent commits** — did a recent change introduce this?
3. **Check test coverage** — is the affected area tested?
4. **Check error logs** — are there related stack traces?

This investigation is best-effort and should take no more than 2 minutes. If the root cause is not quickly apparent, note it as "Requires investigation" in the report.

---

## Phase 2: DOCUMENT

Create a structured bug report with all required fields.

### 2.1 Auto-Increment Bug Number

```bash
# Find the next bug number for this category
# Scan existing files: BUG-{category}-{NNN}.md
# Find the highest NNN and increment

EXISTING=$(ls .claude/PRPs/qa/bugs/BUG-{category}-*.md 2>/dev/null | \
  grep -oP '\d+(?=\.md$)' | sort -n | tail -1)
NEXT_NUM=$(printf "%03d" $((${EXISTING:-0} + 1)))
```

### 2.2 Bug Report Template

```markdown
# BUG-{category}-{number}: {title}

**Severity**: P{N}
**Category**: {category}
**Status**: OPEN
**Filed**: {YYYY-MM-DD HH:MM}
**Author**: Claude (via /prp-bug)

---

## Description

{Detailed description of the bug, expanded from the original report}

## Steps to Reproduce

### Arrange
{Setup required to trigger the bug — environment, data, preconditions}

### Act
{Exact steps to trigger the bug}
1. {step 1}
2. {step 2}
3. {step 3}

### Assert
{What you observe vs. what you expected}

## Expected Behavior

{What should happen}

## Actual Behavior

{What actually happens — include error messages, stack traces, screenshots if available}

## Environment

| Property | Value |
|----------|-------|
| Project | {project name} |
| Branch | {current git branch} |
| Commit | {short SHA} |
| OS | {detected OS} |
| Runtime | {Node version / Python version / etc.} |
| Framework | {detected framework + version} |

## Root Cause Analysis

{If determinable from investigation:}
{- Which file/function is responsible}
{- Why the bug exists (logic error, missing validation, race condition, etc.)}
{- When it was introduced (commit SHA if identifiable)}

{If not determinable:}
Requires further investigation. Suggested starting points:
- {file or area to examine}
- {relevant test to write}

## Suggested Fix

{Concrete suggestion for how to fix the bug:}
{- Which file(s) to modify}
{- What change to make}
{- What tests to add}

{If unclear:}
Investigation needed before a fix can be proposed.

## Related

- **Affected files**: {list of files involved}
- **Related tests**: {existing test files for the affected area, or "none"}
- **Related bugs**: {any similar open bugs, or "none"}

---

## Resolution

**Status**: OPEN
**Resolved**: —
**Fix commit**: —
**Verified by**: —
```

---

## Phase 3: SAVE

### 3.1 Ensure Directory Exists

```bash
mkdir -p .claude/PRPs/qa/bugs
```

### 3.2 Write Bug File

Save to `.claude/PRPs/qa/bugs/BUG-{category}-{number}.md`.

Example filenames:
- `BUG-security-001.md`
- `BUG-functionality-012.md`
- `BUG-performance-003.md`
- `BUG-ui-007.md`

### 3.3 Confirm Save

```
Bug filed: .claude/PRPs/qa/bugs/BUG-{category}-{number}.md
```

---

## Phase 4: LINK

Optionally create a corresponding item in an external tracker.

### 4.1 Plane Integration

If `.claude/prp-settings.json` has `plane.workspace_slug` and `plane.project_id` configured, and `PLANE_API_KEY` is set:

- Create a Plane work item using the Plane MCP tools (if available) or the Plane API:
  - Title: `[BUG] {title}`
  - Description: Link to the bug file + summary
  - Priority: Map P0=urgent, P1=high, P2=medium, P3=low, P4=none
  - Label: `bug`

Note the Plane issue ID in the bug report under "Related".

### 4.2 GitHub Issues

If `gh` CLI is available and the project is a GitHub repo:

```bash
# Check if gh is available and authenticated
gh auth status 2>/dev/null
```

If available, offer to create a GitHub issue:

```bash
gh issue create \
  --title "[BUG][P{N}] {title}" \
  --body "Filed via /prp-bug. See .claude/PRPs/qa/bugs/BUG-{category}-{number}.md for full report." \
  --label "bug,P{N}"
```

Only create the external issue if the user confirms, or if `$ARGUMENTS` includes `--link`.

### 4.3 Skip Linking

If neither Plane nor GitHub is available, skip linking silently. The bug file on disk is the primary record.

---

## Output

Present a summary to the user:

```
Bug Report Filed
================

File:     .claude/PRPs/qa/bugs/BUG-{category}-{number}.md
Title:    {title}
Severity: P{N} ({severity label})
Category: {category}
Status:   OPEN

{If root cause was found}
Root Cause: {brief description}
Suggested Fix: {brief description}

{If external issue was created}
Plane:    {workspace}/issues/{id}
GitHub:   #{issue_number}

{If P0 or P1}
WARNING: This is a {P0/P1} bug. Consider running `/prp-qa-gate` to check release readiness.
```

The primary output is the **bug file written to disk**. The summary is conversational.
