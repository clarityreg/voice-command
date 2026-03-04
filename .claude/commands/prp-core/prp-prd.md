---
description: Generate a problem-first, hypothesis-driven Product Requirements Document
argument-hint: <feature-description>
---

# Product Requirements Document Generator

You are about to create a PRD using a problem-first, hypothesis-driven approach. This is an interactive process that discovers requirements through targeted questions rather than assumptions.

## Core Philosophy

- **Start with problems, not solutions** - Understand what's broken before proposing fixes
- **Demand evidence** - No building without validation of assumptions
- **Think in hypotheses** - Every feature is a bet that can be tested
- **Reject filler content** - If information is missing, mark it as `[TBD - needs discovery]`

---

## Phase 1: INITIATE

**Parse the input:**
- If `$ARGUMENTS` contains a description, use it as the starting point
- If empty, ask: "What are we building? Describe the feature or problem in 2-3 sentences."

**Clarify scope:**
1. Is this a new feature, enhancement, or fix?
2. Do we have an existing codebase to integrate with?
3. What's the rough timeline expectation?

---

## Phase 2: FOUNDATION - Problem Discovery

Ask these questions (skip if already answered):

### The Five Core Questions

1. **WHO** is experiencing the problem?
   - Primary users affected
   - Secondary stakeholders
   - Who benefits if solved?

2. **WHAT** is the actual problem?
   - Current pain points (be specific)
   - What are users trying to accomplish?
   - What happens when they fail?

3. **WHY** can't they solve it today?
   - Existing workarounds
   - Why those workarounds are insufficient
   - What's blocking a solution?

4. **WHY NOW**?
   - What changed that makes this urgent?
   - What's the cost of not solving it?
   - External pressures or opportunities

5. **HOW** will we know it's solved?
   - Observable behavior changes
   - Measurable improvements
   - Success criteria (quantified if possible)

---

## Phase 3: GROUNDING - Market Context

Use web research to gather:

1. **Competitor Analysis**
   - How do similar products solve this?
   - What patterns work? What fails?

2. **Industry Standards**
   - Best practices for this type of feature
   - Common pitfalls to avoid

3. **User Expectations**
   - What do users expect from similar solutions?
   - Mental models to align with

---

## Phase 4: DEEP DIVE - Vision & Users

### User Profiles

For each user type, define:
- **Role**: Who are they?
- **Goal**: What do they want to accomplish?
- **Pain**: What frustrates them today?
- **Behavior**: How do they currently work?

### Success Scenarios

Write 2-3 concrete scenarios:
- "When [user] needs to [task], they will [action] and see [result]"

---

## Phase 5: GROUNDING - Technical Assessment

If there's an existing codebase:

1. **Use the Explore agent** to understand:
   - Current architecture patterns
   - Related existing features
   - Technical constraints or debt

2. **Feasibility Check**:
   - What's technically possible within constraints?
   - What dependencies exist?
   - What risks are involved?

---

## Phase 6: DECISIONS

Finalize:

1. **Scope Definition**
   - What's IN scope (MVP)
   - What's explicitly OUT of scope
   - Future considerations (v2+)

2. **Approach Selection**
   - Recommended technical approach
   - Alternatives considered
   - Why this approach was chosen

3. **Hypotheses to Test**
   - List testable assumptions
   - How each could be validated
   - What would invalidate them

---

## Phase 7: GENERATE - Create the PRD

Write the document to `.claude/PRPs/prds/{kebab-case-name}.prd.md`:

```markdown
# PRD: {Feature Name}

**Status**: Draft | Ready for Review | Approved
**Author**: Claude + {User}
**Created**: {date}
**Last Updated**: {date}

---

## Problem Statement

### The Problem
{2-3 sentences describing the core problem}

### Evidence
- {Concrete evidence point 1}
- {Concrete evidence point 2}

### Impact
- **Users affected**: {number/description}
- **Frequency**: {how often this problem occurs}
- **Severity**: {Critical | High | Medium | Low}

---

## Proposed Solution

### Overview
{High-level description of the solution approach}

### Key Hypotheses

| Hypothesis | Test Method | Success Criteria |
|------------|-------------|------------------|
| {belief 1} | {how to test} | {what proves it} |
| {belief 2} | {how to test} | {what proves it} |

### What We're NOT Building
- {Explicitly excluded item 1}
- {Explicitly excluded item 2}

---

## User Context

### Primary Users
**{User Type 1}**
- Goal: {what they want}
- Pain: {current frustration}
- Success: {what good looks like}

### User Stories
- As a {user}, I want to {action} so that {benefit}
- As a {user}, I want to {action} so that {benefit}

---

## Technical Approach

### Architecture
{High-level technical approach}

### Dependencies
- {dependency 1}
- {dependency 2}

### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| {risk 1} | {H/M/L} | {H/M/L} | {plan} |

---

## Success Metrics

### Primary Metrics
- {metric 1}: {current} → {target}
- {metric 2}: {current} → {target}

### Validation Approach
- {How we'll measure success}
- {Timeline for validation}

---

## Implementation Phases

### Phase 1: {name} ({scope})
- {deliverable 1}
- {deliverable 2}

### Phase 2: {name} ({scope})
- {deliverable 1}
- {deliverable 2}

---

## Open Questions
- [ ] {question needing answer}
- [ ] {question needing answer}

## Decision Log
| Date | Decision | Rationale |
|------|----------|-----------|
| {date} | {decision} | {why} |

---
*This PRD is ready for planning with `/prp-plan`*
```

---

## Phase 8: OUTPUT

Report to the user:

```
PRD Created: .claude/PRPs/prds/{name}.prd.md

Summary:
- Problem: {one-line summary}
- Solution: {one-line summary}
- Key Hypotheses: {count}
- Open Questions: {count}

Next Steps:
1. Review the PRD and refine open questions
2. When ready, generate implementation plan: /prp-plan .claude/PRPs/prds/{name}.prd.md
```

---

## Quality Checklist

Before finalizing, verify:

- [ ] Problem is clearly stated with evidence
- [ ] Solution addresses the stated problem
- [ ] Hypotheses are testable
- [ ] Out-of-scope is explicitly defined
- [ ] Success metrics are measurable
- [ ] Risks are identified with mitigations
- [ ] No filler content - all sections have real information or are marked [TBD]
