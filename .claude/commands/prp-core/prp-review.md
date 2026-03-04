---
description: Perform senior-level code review on a GitHub pull request
argument-hint: <PR-number or URL>
---

# Pull Request Code Review Protocol

You are about to perform a comprehensive code review using the `gh` CLI tool. This follows a senior-level review process focusing on correctness, patterns, and maintainability.

## Review Philosophy

- **Be constructive and actionable** - Every criticism comes with a suggestion
- **Check implementation artifacts** - Documented deviations are intentional decisions
- **Balance specificity with severity** - Not every issue is critical
- **Acknowledge strengths** - Good code deserves recognition

---

## Phase 1: FETCH

### Parse Input

```bash
# Determine PR reference from $ARGUMENTS
# Supports: PR number (123), URL (https://github.com/owner/repo/pull/123)
```

### Retrieve PR Context

```bash
# Get PR metadata
gh pr view {number} --json number,title,body,author,baseRefName,headRefName,files,additions,deletions,state

# Get changed files
gh pr diff {number} --name-only

# Checkout the branch for local analysis
gh pr checkout {number}
```

### Validate Reviewable State

- [ ] PR is open (not merged/closed)
- [ ] No merge conflicts
- [ ] Branch is up to date with base

---

## Phase 2: CONTEXT

### Read Project Rules

1. Check for `CLAUDE.md` in repo root
2. Check for `.claude/` configuration
3. Note any project-specific review guidelines

### Locate Implementation Artifacts

```bash
# Check for related plan or issue artifacts
ls .claude/PRPs/plans/ .claude/PRPs/issues/ 2>/dev/null
```

If artifacts exist, read them to understand:
- Intended approach
- Documented deviations (these are OK)
- Acceptance criteria

### Determine PR Intent

Categorize the PR:
- **Feature**: New functionality
- **Fix**: Bug correction
- **Refactor**: Code improvement without behavior change
- **Docs**: Documentation only
- **Test**: Test additions/changes
- **Chore**: Build, config, dependency updates

### Map Changed Files

Group files by category:
- Source code
- Tests
- Configuration
- Documentation

---

## Phase 3: REVIEW

Analyze code against these criteria:

### 3.1 Correctness
- Does the code do what it claims?
- Are edge cases handled?
- Are error conditions managed properly?

### 3.2 Type Safety
- Are types properly defined?
- Any `any` types that should be specific?
- Proper null/undefined handling?

### 3.3 Pattern Compliance
- Does it follow project conventions?
- Consistent naming and structure?
- Reuses existing utilities?

### 3.4 Security
- Input validation present?
- No hardcoded secrets?
- Proper access controls?

### 3.5 Performance
- Obvious inefficiencies?
- N+1 queries?
- Unnecessary re-renders (React)?

### 3.6 Completeness
- Tests included for new code?
- Documentation updated?
- Types exported if needed?

### 3.7 Maintainability
- Code is readable?
- Comments where needed?
- No magic numbers/strings?

### Issue Severity Levels

| Level | Description | Action |
|-------|-------------|--------|
| **Critical** | Breaks functionality, security risk | Must fix before merge |
| **High** | Logic error, missing tests | Should fix |
| **Medium** | Style violation, minor inefficiency | Nice to fix |
| **Low** | Nitpick, suggestion | Optional |

---

## Phase 4: VALIDATE

Run automated checks:

```bash
# Type checking (detect package manager first)
npm run typecheck || yarn typecheck || pnpm typecheck

# Linting
npm run lint || yarn lint || pnpm lint

# Tests
npm test || yarn test || pnpm test

# Build
npm run build || yarn build || pnpm build
```

Capture results for each:
- [ ] Types: Pass / Fail
- [ ] Lint: Pass / Fail (+ warning count)
- [ ] Tests: Pass / Fail (+ coverage if available)
- [ ] Build: Pass / Fail

---

## Phase 5: DECIDE

### Decision Matrix

| Condition | Recommendation |
|-----------|----------------|
| No issues, all checks pass | **Approve** |
| Low/Medium issues only, checks pass | **Approve with comments** |
| High issues OR check failures | **Request Changes** |
| Critical issues | **Block** |

### Form Recommendation

Based on findings, select:
- `APPROVE` - Ready to merge
- `COMMENT` - Feedback without blocking
- `REQUEST_CHANGES` - Must address before merge

---

## Phase 6: REPORT

Save review to `.claude/PRPs/reviews/pr-{NUMBER}-review.md`:

```markdown
# PR Review: #{number} - {title}

**Reviewer**: Claude
**Date**: {date}
**Decision**: {Approve | Request Changes | Comment}

---

## Summary

{2-3 sentence overview of the PR and findings}

---

## Issues Found

### Critical
{None or list with file:line references}

### High
{None or list}

### Medium
{None or list}

### Low
{None or list}

---

## Validation Results

| Check | Status | Notes |
|-------|--------|-------|
| Types | {Pass/Fail} | {details} |
| Lint | {Pass/Fail} | {details} |
| Tests | {Pass/Fail} | {details} |
| Build | {Pass/Fail} | {details} |

---

## Strengths

- {Positive observation 1}
- {Positive observation 2}

---

## Recommendation

**{APPROVE | REQUEST_CHANGES | COMMENT}**

{Reasoning for the decision}

---

## Required Actions
{If requesting changes}
1. {Action item 1}
2. {Action item 2}

## Suggested Improvements
{Optional improvements}
1. {Suggestion 1}
2. {Suggestion 2}
```

---

## Phase 7: PUBLISH

Post the review to GitHub:

```bash
# For approval
gh pr review {number} --approve --body-file .claude/PRPs/reviews/pr-{number}-review.md

# For requesting changes
gh pr review {number} --request-changes --body-file .claude/PRPs/reviews/pr-{number}-review.md

# For comment only
gh pr review {number} --comment --body-file .claude/PRPs/reviews/pr-{number}-review.md
```

---

## Phase 8: OUTPUT

Report to user:

```
PR Review Complete: #{number}

Decision: {Approve | Request Changes | Comment}

Issues Found:
- Critical: {count}
- High: {count}
- Medium: {count}
- Low: {count}

Validation:
- Types: {status}
- Lint: {status}
- Tests: {status}
- Build: {status}

Review posted to GitHub and saved to:
.claude/PRPs/reviews/pr-{number}-review.md

Next Steps:
{Based on decision - what author should do}
```

---

## Review Checklist Quick Reference

### Must Check
- [ ] All tests pass
- [ ] No type errors
- [ ] No lint errors
- [ ] Build succeeds
- [ ] No security issues
- [ ] Error handling present

### Should Check
- [ ] Test coverage adequate
- [ ] Documentation updated
- [ ] Follows project patterns
- [ ] No obvious performance issues

### Nice to Check
- [ ] Code is readable
- [ ] Good naming
- [ ] Comments where helpful
