---
description: Investigate a GitHub issue and create an implementation artifact
argument-hint: <issue-number or URL or description>
---

# Issue Investigation Workflow

Systematically investigate GitHub issues and create detailed implementation artifacts, with optional Archon task creation for tracking.

## Investigation Philosophy

- **5 Whys for bugs** - Dig to root cause, not symptoms
- **Codebase evidence** - Reference actual files and line numbers
- **Concrete findings** - No assumptions without evidence
- **Archon tracking** - Create tasks for implementation follow-up

---

## Phase 1: PARSE

### Identify Input Type

| Input | Detection | Action |
|-------|-----------|--------|
| Issue Number | `#123` or just `123` | Fetch from GitHub |
| GitHub URL | Contains `github.com` | Extract owner/repo/number |
| Free-form | No pattern match | Treat as issue description |

### Fetch Issue Context (GitHub)

```bash
# Get issue details
gh issue view {number} --json number,title,body,labels,comments,author,createdAt

# Extract relevant fields
ISSUE_TITLE="{title}"
ISSUE_BODY="{body}"
ISSUE_LABELS="{labels}"
```

### Classify Issue Type

| Type | Indicators |
|------|------------|
| **Bug** | "doesn't work", "error", "broken", "fails" |
| **Enhancement** | "add", "improve", "support", "would be nice" |
| **Refactor** | "cleanup", "technical debt", "reorganize" |
| **Chore** | "update", "upgrade", "maintenance" |
| **Documentation** | "docs", "readme", "comments" |

---

## Phase 2: EXPLORE

**Use the Explore agent** to search the codebase:

```
Launch Task tool with subagent_type="Explore"

Prompt: "Investigate issue: {issue_title}

Search for:
1. Files related to: {keywords from issue}
2. Similar patterns or implementations
3. Integration points that may be affected
4. Existing test coverage for affected areas
5. Recent changes to relevant files (git history)

Return actual file paths with line numbers and brief explanations."
```

### Discovery Targets

1. **Relevant Files**
   - Files mentioned in the issue
   - Files matching keywords
   - Related components/modules

2. **Integration Points**
   - What depends on affected code
   - What the affected code depends on

3. **Similar Patterns**
   - How similar issues were fixed
   - Existing patterns to follow

4. **Test Structure**
   - Existing tests for the area
   - Test utilities available

---

## Phase 3: ANALYZE

### 3.1 Root Cause Analysis (for bugs)

Apply the 5 Whys method:

```markdown
### Why #1
**Question**: Why does {symptom} occur?
**Answer**: Because {cause}
**Evidence**: {file:line}

### Why #2
**Question**: Why does {cause} happen?
**Answer**: Because {deeper cause}
**Evidence**: {file:line}

[Continue until root cause identified]

### Root Cause
{The fundamental issue that needs to be fixed}
**Location**: {file:line}
```

### 3.2 Scope Analysis (for enhancements)

```markdown
### Scope Boundaries

**In Scope**:
- {specific change 1}
- {specific change 2}

**Out of Scope**:
- {related but not included}

**Dependencies**:
- {what this depends on}

**Dependents**:
- {what depends on this}
```

### 3.3 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| {risk 1} | H/M/L | H/M/L | {plan} |
| {risk 2} | H/M/L | H/M/L | {plan} |

### 3.4 Edge Cases

| Case | Expected Behavior | Notes |
|------|-------------------|-------|
| {edge case 1} | {behavior} | {notes} |
| {edge case 2} | {behavior} | {notes} |

---

## Phase 4: GENERATE

Create artifact at `.claude/PRPs/issues/issue-{number}.md`:

```markdown
# Issue Investigation: #{number} - {title}

**Investigated**: {date}
**Status**: Ready for Implementation
**Type**: {Bug | Enhancement | Refactor | Chore | Documentation}
**Archon Task ID**: {task_id or "Not created"}

---

## Problem Statement

{Clear description of the issue}

### Reproduction (for bugs)
1. {step 1}
2. {step 2}
3. Expected: {expected}
4. Actual: {actual}

---

## Analysis

### Root Cause (for bugs)
{Explanation of why this happens}
**Location**: `{file}:{line}`

### Scope (for enhancements)
{What needs to change}

### Impact Assessment

| Aspect | Impact |
|--------|--------|
| Users Affected | {description} |
| Code Areas | {files/modules} |
| Risk Level | {Low/Medium/High} |

---

## Implementation Plan

### Approach
{High-level approach to fixing/implementing}

### Files to Modify

| File | Change | Lines |
|------|--------|-------|
| `{path}` | {description} | {lines} |

### Files to Create

| File | Purpose |
|------|---------|
| `{path}` | {description} |

### Implementation Steps

1. **{Step 1}**
   - {detail}
   - Validation: `{command}`

2. **{Step 2}**
   - {detail}
   - Validation: `{command}`

---

## Patterns to Follow

### From Codebase

| Pattern | Source | Apply To |
|---------|--------|----------|
| {pattern} | `{file}:{lines}` | {where to use} |

### Error Handling
{Reference existing error handling pattern}

### Testing
{Reference existing test pattern}

---

## Validation

### Automated
```bash
{type check command}
{lint command}
{test command}
```

### Manual
- [ ] {manual verification step 1}
- [ ] {manual verification step 2}

---

## Edge Cases

| Case | Expected Behavior | Test |
|------|-------------------|------|
| {case} | {behavior} | {test reference} |

---

## Confidence Assessment

| Aspect | Level | Reasoning |
|--------|-------|-----------|
| Root Cause | {High/Medium/Low} | {one sentence} |
| Fix Approach | {High/Medium/Low} | {one sentence} |
| Risk | {High/Medium/Low} | {one sentence} |

---

*Ready for implementation with `/prp-issue-fix`*
```

---

## Phase 5: COMMIT

Save the artifact:

```bash
git add .claude/PRPs/issues/issue-{number}.md
git commit -m "chore(prp): investigate issue #{number}

Created investigation artifact with:
- Root cause analysis
- Implementation plan
- Validation approach

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 6: CREATE ARCHON TASK

**If Archon MCP is available:**

```python
# 1. Find or create project for this component
projects = find_projects(query="<component-name>")

if projects:
    project_id = projects[0]["id"]
else:
    # Create new project for this component
    project = manage_project(
        "create",
        title="<Component> Fixes",
        description="Bug fixes and improvements for <component>"
    )
    project_id = project["project_id"]

# 2. Create task for the fix
task = manage_task(
    "create",
    project_id=project_id,
    title=f"Fix: #{issue_number} - {issue_title}",
    description=f"See: .claude/PRPs/issues/issue-{issue_number}.md",
    status="todo"
)

# 3. Update artifact with task ID
# Add to artifact metadata:
archon_task_id = task["task_id"]
```

**Update artifact frontmatter:**
```yaml
archon_task_id: "task-abc123"
archon_project_id: "proj-xyz789"
```

**Fallback (Archon not available):**
- Log: "Archon not configured, skipping task creation"
- Artifact remains valid without Archon tracking

---

## Phase 7: POST TO GITHUB (if issue from GitHub)

Post investigation summary to GitHub issue:

```bash
gh issue comment {number} --body "## Investigation Complete

**Type**: {type}
**Confidence**: {confidence level}

### Summary
{2-3 sentence summary}

### Root Cause
{Brief root cause description}

### Files Affected
- \`{file1}\`
- \`{file2}\`

### Next Steps
Implementation artifact created: \`.claude/PRPs/issues/issue-{number}.md\`

---
*Investigated by Claude Code*"
```

**Skip this phase if input was free-form description (not GitHub issue).**

---

## Phase 8: REPORT

Output to user:

```
Investigation Complete: #{number}

Type: {Bug | Enhancement | Refactor}
Confidence: {High | Medium | Low}

Findings:
- Root Cause: {brief description}
- Files Affected: {count}
- Implementation Steps: {count}

Archon Integration:
- Task Created: {task_id or "Not configured"}
- Project: {project_id or "N/A"}

Artifact: .claude/PRPs/issues/issue-{number}.md

Next Steps:
1. Review the investigation artifact
2. When ready: /prp-issue-fix .claude/PRPs/issues/issue-{number}.md
```

---

## Severity/Priority Guidelines

### Severity (Impact)

| Level | Definition |
|-------|------------|
| **Critical** | System unusable, data loss, security issue |
| **High** | Major feature broken, no workaround |
| **Medium** | Feature degraded, workaround exists |
| **Low** | Minor issue, cosmetic, edge case |

### Priority (Urgency)

| Level | Definition |
|-------|------------|
| **P0** | Fix immediately, block release |
| **P1** | Fix this sprint |
| **P2** | Fix this quarter |
| **P3** | Fix when convenient |

### Complexity

| Level | Definition |
|-------|------------|
| **Trivial** | One-line fix, obvious |
| **Simple** | Single file, clear approach |
| **Moderate** | Multiple files, some complexity |
| **Complex** | System-wide, requires design |
