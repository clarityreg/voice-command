---
description: Execute an implementation plan with Archon task tracking
argument-hint: <plan-file-path>
---

# Implementation Plan Executor

Execute implementation plans with rigorous validation and Archon task lifecycle management.

## Core Principles

- **VALIDATION LOOPS** - Run checks after every change, fix immediately
- **ARCHON TRACKING** - Update task status throughout implementation
- **ONE TASK AT A TIME** - Complete each task before starting next
- **MANDATORY TESTING** - Write or update tests for new code

---

## Phase 1: DETECT

Identify package manager and validation tooling:

```bash
# Check for lock files
if [[ -f "bun.lockb" ]]; then
    PKG_MGR="bun"
elif [[ -f "pnpm-lock.yaml" ]]; then
    PKG_MGR="pnpm"
elif [[ -f "yarn.lock" ]]; then
    PKG_MGR="yarn"
elif [[ -f "package-lock.json" ]]; then
    PKG_MGR="npm"
elif [[ -f "Cargo.toml" ]]; then
    PKG_MGR="cargo"
elif [[ -f "pyproject.toml" ]]; then
    PKG_MGR="poetry"
elif [[ -f "requirements.txt" ]]; then
    PKG_MGR="pip"
fi
```

Store for use in validation commands.

---

## Phase 2: LOAD

### 2.1 Read Plan File

Parse `$ARGUMENTS` for plan file path:

```bash
PLAN_FILE="$ARGUMENTS"
if [[ ! -f "$PLAN_FILE" ]]; then
    echo "Plan file not found: $PLAN_FILE"
    exit 1
fi
```

### 2.2 Extract Plan Components

From the plan document, extract:
- Task list with statuses
- Mandatory reading files
- Validation commands
- Success criteria

### 2.3 Archon Task Mapping

**If plan has Archon integration:**

```python
# 1. Extract archon_project_id from plan frontmatter
project_id = plan_frontmatter.get("archon_project_id")

# 2. Get current task list from Archon
if project_id:
    archon_tasks = find_tasks(
        filter_by="project",
        filter_value=project_id
    )

    # 3. Map plan tasks to Archon task IDs
    task_mapping = {}
    for plan_task in plan_tasks:
        for archon_task in archon_tasks:
            if plan_task["name"] in archon_task["title"]:
                task_mapping[plan_task["name"]] = archon_task["id"]
```

**If no Archon project exists but Archon is available:**

```python
# Create project now
project = manage_project(
    "create",
    title=plan_title,
    description=plan_overview
)
project_id = project["project_id"]

# Create all tasks
for task in plan_tasks:
    manage_task(
        "create",
        project_id=project_id,
        title=task["name"],
        status="todo"
    )
```

**Fallback (Archon not available):**
- Log: "Archon not configured, using file-based tracking"
- Track status in plan document checkboxes only

---

## Phase 3: PREPARE

### 3.1 Git State

```bash
# Verify clean working directory
git status --porcelain

# Create feature branch if not already on one
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" ]]; then
    FEATURE_BRANCH="feat/$(echo $PLAN_NAME | tr ' ' '-' | tr '[:upper:]' '[:lower:]')"
    git checkout -b "$FEATURE_BRANCH"
fi

# Ensure up to date with remote
git pull origin "$CURRENT_BRANCH" --rebase 2>/dev/null || true
```

### 3.2 Mandatory Reading

Before implementation, read all files in the mandatory reading list:

```
For each file in mandatory_reading:
1. Read the specified file
2. Focus on the noted line ranges
3. Understand the patterns to follow
```

---

## Phase 4: EXECUTE

For each task in sequence:

### 4.1 Start Task (Archon)

```python
# Update Archon status
if archon_available and task_id:
    manage_task(
        "update",
        task_id=task_id,
        status="doing"
    )
```

Log task start:
```
Starting: {task_name}
Archon Status: doing
```

### 4.2 Implement

Execute the implementation:

1. **Read relevant files** from mandatory reading
2. **Follow patterns** documented in the plan
3. **Write code** matching existing style
4. **Create tests** for new functionality

### Implementation Rules

- Follow file naming conventions from codebase
- Reuse existing utilities and helpers
- Match error handling patterns
- Include TypeScript types (if TS project)
- Add comments only where logic isn't obvious

### 4.3 Immediate Validation

After EACH change, run validation:

```bash
# Type checking
$PKG_MGR run typecheck 2>&1 || true

# Linting (auto-fix)
$PKG_MGR run lint --fix 2>&1 || true
```

**If validation fails:**
1. Stop implementation
2. Fix the issue immediately
3. Re-run validation
4. Only proceed when clean

### 4.4 Task Completion

When task implementation is complete:

```python
# Move to review status
if archon_available and task_id:
    manage_task(
        "update",
        task_id=task_id,
        status="review"
    )
```

**DO NOT mark as "done" yet** - this comes after full validation.

### 4.5 Document Deviations

If you must deviate from the plan:

```markdown
## Deviation Log

### Task: {task_name}
**Planned**: {what the plan said}
**Actual**: {what was done instead}
**Reason**: {why the deviation was necessary}
```

---

## Phase 5: VALIDATE

After ALL tasks are in "review" status, run full validation:

### 5.1 Static Analysis

```bash
# Type checking
$PKG_MGR run typecheck

# Linting
$PKG_MGR run lint
```

### 5.2 Unit Tests

```bash
# Run tests with coverage
$PKG_MGR test -- --coverage

# Or for Python
PYTHONPATH=. pytest tests/ -v --cov
```

**MANDATORY**: If tests don't exist, write them before proceeding.

### 5.3 Build Verification

```bash
$PKG_MGR run build
```

### 5.4 Custom Validation

Run any task-specific validation commands from the plan.

### Validation Results

| Check | Status | Notes |
|-------|--------|-------|
| Types | Pass/Fail | {details} |
| Lint | Pass/Fail | {details} |
| Tests | Pass/Fail | {coverage %} |
| Build | Pass/Fail | {details} |

**If ANY validation fails:**
1. Do not proceed to Phase 6
2. Fix the issues
3. Re-run validation
4. Repeat until all pass

---

## Phase 6: FINALIZE

### 6.1 Complete Archon Tasks

For each task that passed validation:

```python
if archon_available:
    manage_task(
        "update",
        task_id=task_id,
        status="done"
    )
```

For tasks without test coverage:
- Leave in "review" status
- Add note: "Awaiting test coverage"

### 6.2 Update Plan Document

Mark completed tasks in the plan file:

```markdown
#### Task 1.1: Setup Authentication
**Status**: done ✓
**Archon Task ID**: task-abc123
```

### 6.3 Commit Changes

```bash
git add -A
git commit -m "feat({scope}): implement {feature-name}

- Completed tasks: {count}
- Tests added: {count}
- Coverage: {percentage}%

Plan: .claude/PRPs/plans/{name}.plan.md
{Archon Project ID if available}

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 7: REPORT

Generate implementation report:

```markdown
# Implementation Report: {Feature Name}

**Date**: {date}
**Plan**: {plan_file}
**Archon Project**: {project_id or "N/A"}

---

## Summary

- Total Tasks: {count}
- Completed: {count}
- In Review: {count} (awaiting tests)
- Remaining: {count}

## Validation Results

| Check | Status |
|-------|--------|
| Types | {Pass/Fail} |
| Lint | {Pass/Fail} |
| Tests | {Pass/Fail} ({coverage}%) |
| Build | {Pass/Fail} |

## Files Changed

{List of files created/modified}

## Deviations from Plan

{Any documented deviations}

## Next Steps

1. {If incomplete: what remains}
2. {If complete: suggest PR creation}
```

---

## Output to User

```
Implementation Complete

Plan: {plan_file}
Tasks: {completed}/{total}

Archon Status:
- Project: {project_id or "Not configured"}
- Tasks Done: {count}
- Tasks In Review: {count}

Validation:
- Types: {status}
- Lint: {status}
- Tests: {status} ({coverage}%)
- Build: {status}

Next Steps:
{If all pass}: Create PR with /prp-pr
{If tests missing}: Add tests for remaining tasks
{If validation failed}: Fix issues and re-run
```

---

## Workflow Rules

1. **NEVER** skip Archon task updates (if available)
2. **NEVER** proceed with failing validation
3. **ALWAYS** write tests for new code
4. **ALWAYS** follow patterns from mandatory reading
5. **DOCUMENT** any deviations from the plan
6. **ONE** task in "doing" status at a time

---

## Error Handling

### Archon Operations Fail

```python
try:
    manage_task("update", ...)
except Exception as e:
    log_warning(f"Archon update failed: {e}")
    # Continue with file-based tracking
    update_plan_document_status(task_name, status)
```

### Validation Fails

1. Stop implementation
2. Identify failing check
3. Fix the issue
4. Re-run ALL validation
5. Only proceed when clean

### Plan Not Found

```
Error: Plan file not found: {path}

Available plans:
{list .claude/PRPs/plans/*.plan.md}

Usage: /prp-implement <plan-file-path>
```

---

## Archon Task Lifecycle Summary

```
todo → doing → review → done
       │         │        │
       │         │        └── After validation passes
       │         └── After implementation complete
       └── When starting task
```

**Status Transitions:**
- `todo` → `doing`: When starting work on a task
- `doing` → `review`: When implementation is complete
- `review` → `done`: After validation passes with test coverage
