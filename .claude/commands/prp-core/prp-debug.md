---
description: Root cause analysis using systematic hypothesis testing
argument-hint: <symptom-description or issue>
---

# Root Cause Analysis Protocol

You are about to perform systematic root cause analysis. This protocol identifies actual causes rather than symptoms through hypothesis-driven investigation.

## Core Principles

- **Reject conjecture** - No "likely" or "probably" without evidence
- **Require concrete evidence** - File:line references, not assumptions
- **Test, don't assume** - Verify each hypothesis
- **Consult git history** - `git blame` and `git log` are your friends
- **Stop at changeable code** - Root cause is code you can modify

**The Ultimate Test**: "If I changed THIS specific thing, would the issue vanish?"

---

## Phase 1: CLASSIFY

### Parse Input

If `$ARGUMENTS` is provided:
- Determine if it's a raw symptom or pre-diagnosed issue
- Extract any file paths, error messages, or stack traces

### Establish Analysis Mode

| Mode | When to Use |
|------|-------------|
| **Quick** | Clear error message, obvious location |
| **Deep** | Intermittent issue, unclear cause |

### Restate the Problem

Write a clear problem statement:
```
SYMPTOM: {What is happening}
EXPECTED: {What should happen}
CONTEXT: {When/where it occurs}
```

---

## Phase 2: HYPOTHESIZE

Generate 2-4 competing theories ranked by likelihood:

```markdown
## Hypothesis 1: {Theory Name} [Likelihood: High/Medium/Low]

**Conditions that must exist:**
- {condition 1}
- {condition 2}

**Evidence required to confirm:**
- {evidence 1}
- {evidence 2}

**How to test:**
- {test method}
```

### Hypothesis Generation Guidelines

1. Start with the most common causes
2. Consider recent changes (check `git log`)
3. Think about edge cases and race conditions
4. Don't forget environmental factors

---

## Phase 3: INVESTIGATE - The 5 Whys

Execute the 5 Whys framework systematically:

```markdown
### Why #1
**Question**: Why does {symptom} occur?
**Answer**: Because {cause A}
**Evidence**: {file:line or test result}

### Why #2
**Question**: Why does {cause A} happen?
**Answer**: Because {cause B}
**Evidence**: {file:line or test result}

### Why #3
**Question**: Why does {cause B} happen?
**Answer**: Because {cause C}
**Evidence**: {file:line or test result}

### Why #4
**Question**: Why does {cause C} happen?
**Answer**: Because {cause D}
**Evidence**: {file:line or test result}

### Why #5
**Question**: Why does {cause D} happen?
**Answer**: Because {ROOT CAUSE}
**Evidence**: {file:line - THIS IS THE CODE TO CHANGE}
```

### Investigation Tools

Use these to gather evidence:

```bash
# Find related code
grep -r "error_pattern" --include="*.{ext}"

# Check git history
git log --oneline -20 -- {file}
git blame {file} | grep -A5 -B5 "line_number"

# Find callers/dependencies
grep -r "function_name" --include="*.{ext}"
```

---

## Phase 4: VALIDATE

Apply three validation tests:

### Test 1: Causation
> Does the identified cause directly lead to the symptom?

- [ ] Trace the code path from cause to symptom
- [ ] Verify no intermediate factors

### Test 2: Necessity
> Would the symptom exist without this cause?

- [ ] Consider if the symptom could have other origins
- [ ] Check for multiple contributing factors

### Test 3: Sufficiency
> Is this cause alone sufficient, or are co-factors involved?

- [ ] Identify any environmental requirements
- [ ] Note any timing or ordering dependencies

---

## Phase 5: REPORT

Generate the debug report:

```markdown
# Root Cause Analysis: {Issue Title}

**Date**: {date}
**Severity**: Critical | High | Medium | Low
**Status**: Confirmed | Needs Verification

---

## Summary

**Symptom**: {one-line description}
**Root Cause**: {one-line description}
**Fix Location**: {file:line}

---

## Evidence Chain

1. {Symptom} occurs because {Cause 1}
   - Evidence: {file:line}

2. {Cause 1} happens because {Cause 2}
   - Evidence: {file:line}

3. {Cause 2} happens because {ROOT CAUSE}
   - Evidence: {file:line}

---

## Git History

```bash
# Relevant commits
{git log output showing when the issue was introduced}
```

**Introduced in**: {commit hash} by {author} on {date}
**Change description**: {commit message}

---

## Fix Specification

### Location
`{file}:{line_start}-{line_end}`

### Current Code
```{language}
{problematic code}
```

### Proposed Fix
```{language}
{fixed code}
```

### Why This Fixes It
{Explanation of how the fix addresses the root cause}

---

## Verification Steps

1. {Step to verify the fix works}
2. {Step to verify no regression}
3. {Step to verify edge cases}

---

## Prevention

To prevent similar issues:
- {Recommendation 1}
- {Recommendation 2}
```

---

## Phase 6: OUTPUT

Report to the user:

```
Root Cause Analysis Complete

Symptom: {brief description}
Root Cause: {identified cause}
Location: {file:line}

Confidence: {High | Medium | Low}
Based on: {number} evidence points

Recommended Fix:
{brief description of the fix}

Next Steps:
1. Review the analysis above
2. Implement the proposed fix
3. Run verification steps
4. Consider creating an issue artifact: /prp-issue-investigate
```

---

## Debugging Checklist

Common root causes to consider:

### Data Issues
- [ ] Null/undefined values
- [ ] Type mismatches
- [ ] Invalid state

### Timing Issues
- [ ] Race conditions
- [ ] Async ordering
- [ ] Stale data

### Logic Issues
- [ ] Off-by-one errors
- [ ] Boundary conditions
- [ ] Missing cases

### Environment Issues
- [ ] Configuration differences
- [ ] Dependency versions
- [ ] Resource limits

### Integration Issues
- [ ] API contract violations
- [ ] Schema mismatches
- [ ] Permission problems
