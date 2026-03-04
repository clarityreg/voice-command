---
description: Implement a fix from an investigation artifact with Archon tracking
argument-hint: <issue-artifact-path>
---

# Issue Fix Implementation

Execute fixes from investigation artifacts with validation at every step and Archon task lifecycle management.

## Implementation Philosophy

- **Follow the artifact** - The investigation already did the analysis
- **Validate continuously** - Check after every change
- **Track in Archon** - Update task status throughout
- **Don't deviate silently** - Document any changes from plan

---

## Phase 1: LOAD

### Locate Artifact

Parse `$ARGUMENTS` for artifact path:

```bash
ARTIFACT_FILE="$ARGUMENTS"

# If just issue number provided, construct path
if [[ "$ARTIFACT_FILE" =~ ^[0-9]+$ ]]; then
    ARTIFACT_FILE=".claude/PRPs/issues/issue-${ARTIFACT_FILE}.md"
fi

# Verify exists
if [[ ! -f "$ARTIFACT_FILE" ]]; then
    echo "Artifact not found: $ARTIFACT_FILE"
    exit 1
fi
```

### Parse Artifact

Extract from the artifact:
- Issue number and title
- Implementation steps
- Files to modify/create
- Validation commands
- Patterns to follow
- Archon task ID (if present)

### Load Archon Context

**If artifact has Archon task ID:**

```python
# Extract archon_task_id from artifact frontmatter
archon_task_id = artifact_metadata.get("archon_task_id")
archon_project_id = artifact_metadata.get("archon_project_id")

if archon_task_id:
    # Update status to "doing"
    manage_task(
        "update",
        task_id=archon_task_id,
        status="doing"
    )
    log(f"Archon task {archon_task_id} → doing")
```

**If no Archon task but Archon available:**

```python
# Create task now
task = manage_task(
    "create",
    project_id=archon_project_id or find_or_create_project(),
    title=f"Fix: #{issue_number} - {issue_title}",
    status="doing"
)
archon_task_id = task["task_id"]
```

**Fallback (Archon not available):**
- Log: "Archon not configured, using file-based tracking"
- Continue with implementation

---

## Phase 2: VALIDATE ARTIFACT

Confirm the artifact is still valid:

### 2.1 Check File State

Verify files mentioned in artifact still exist and match expectations:

```bash
# For each file in artifact's "Files to Modify"
for file in $FILES_TO_MODIFY; do
    if [[ ! -f "$file" ]]; then
        echo "Warning: File no longer exists: $file"
    fi
done
```

### 2.2 Verify Root Cause

Re-check that the root cause identified is still present:
- Read the identified location
- Confirm the problematic code is there
- Note if anything has changed since investigation

**If artifact is stale:**
```
Warning: Artifact may be outdated.

Changes detected:
- {file}: {modification}

Options:
1. Re-investigate: /prp-issue-investigate #{number}
2. Proceed with caution (may need adjustments)
```

---

## Phase 3: GIT-CHECK

### Verify Git State

```bash
# Check for uncommitted changes
if [[ -n "$(git status --porcelain)" ]]; then
    echo "Warning: Uncommitted changes present"
    echo "Consider committing or stashing before proceeding"
fi

# Check branch
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" ]]; then
    # Create fix branch
    BRANCH_NAME="fix/issue-${ISSUE_NUMBER}"
    git checkout -b "$BRANCH_NAME"
fi

# Sync with remote
git pull origin "$CURRENT_BRANCH" --rebase 2>/dev/null || true
```

---

## Phase 4: IMPLEMENT

Execute each step from the artifact precisely:

### For Each Implementation Step:

#### 4.1 Announce

```
Implementing Step {N}: {step_title}
Target: {file}:{lines}
```

#### 4.2 Execute

- Follow the artifact's instructions exactly
- Match the patterns referenced in the artifact
- Maintain existing code style

#### 4.3 Immediate Validation

After EACH change:

```bash
# Type check
npm run typecheck || yarn typecheck || pnpm typecheck

# Lint (auto-fix allowed)
npm run lint --fix || yarn lint --fix || pnpm lint --fix
```

**If validation fails:**
1. Stop and fix immediately
2. Do not proceed to next step until clean

#### 4.4 Document Deviations

If you must deviate from the artifact:

```markdown
## Deviation from Artifact

**Step**: {step number}
**Planned**: {what artifact said}
**Actual**: {what was done}
**Reason**: {why deviation was necessary}
```

---

## Phase 5: VERIFY

After ALL implementation steps complete:

### 5.1 Run Artifact Validation Commands

Execute each validation command from the artifact:

```bash
# From artifact's "Validation > Automated" section
{each command listed}
```

### 5.2 Full Test Suite

```bash
npm test || yarn test || pnpm test
```

### 5.3 Build Check

```bash
npm run build || yarn build || pnpm build
```

### 5.4 Manual Verification

Check each item in the artifact's "Validation > Manual" checklist.

### Validation Results

| Check | Status | Notes |
|-------|--------|-------|
| Types | Pass/Fail | |
| Lint | Pass/Fail | |
| Tests | Pass/Fail | |
| Build | Pass/Fail | |
| Manual | Pass/Fail | |

**All must pass before proceeding.**

---

## Phase 6: COMMIT

### Stage Changes

```bash
git add -A
```

### Create Commit

```bash
git commit -m "fix(#{ISSUE_NUMBER}): {brief description}

{Longer description if needed}

Root Cause: {from artifact}
Fix: {what was changed}

Closes #{ISSUE_NUMBER}

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 7: PR

Push and create pull request:

```bash
# Push branch
git push -u origin "$BRANCH_NAME"

# Create PR
gh pr create \
    --title "fix: #{ISSUE_NUMBER} - {title}" \
    --body "## Summary

Fixes #{ISSUE_NUMBER}

### Root Cause
{from artifact}

### Changes
{list of changes}

### Validation
- [x] Types pass
- [x] Lint passes
- [x] Tests pass
- [x] Build passes
- [x] Manual verification complete

### Investigation Artifact
\`.claude/PRPs/issues/issue-${ISSUE_NUMBER}.md\`

---
*Fixed by Claude Code*"
```

---

## Phase 8: REVIEW

Perform self-review of the changes:

### 8.1 Root Cause Alignment

Does the fix actually address the root cause from the artifact?

### 8.2 Pattern Conformance

Does the code follow the patterns referenced in the artifact?

### 8.3 Test Adequacy

Are the changes adequately tested?

### 8.4 Potential Issues

Any concerns or edge cases not covered?

### Review Output

```markdown
## Self-Review: #{ISSUE_NUMBER}

**Root Cause Addressed**: Yes/Partial/No
**Patterns Followed**: Yes/Partial/No
**Test Coverage**: Adequate/Needs Improvement

### Concerns
{Any issues noted}

### Recommendations
{Any follow-up work suggested}
```

---

## Phase 9: ARCHIVE

Move artifact to completed folder:

```bash
mkdir -p .claude/PRPs/issues/completed
mv ".claude/PRPs/issues/issue-${ISSUE_NUMBER}.md" \
   ".claude/PRPs/issues/completed/issue-${ISSUE_NUMBER}.md"

git add .claude/PRPs/issues/
git commit -m "chore(prp): archive completed issue-${ISSUE_NUMBER}"
```

### Complete Archon Task

**If Archon task exists:**

```python
manage_task(
    "update",
    task_id=archon_task_id,
    status="done"
)
log(f"Archon task {archon_task_id} → done")
```

---

## Phase 10: REPORT

Output to user:

```
Fix Implemented: #{ISSUE_NUMBER}

Summary:
- Steps Completed: {count}
- Files Modified: {count}
- Tests: {pass/fail}

Archon Status:
- Task: {task_id or "Not tracked"}
- Status: done

Validation:
- Types: Pass
- Lint: Pass
- Tests: Pass
- Build: Pass

PR Created: {url}

Artifact archived to: .claude/PRPs/issues/completed/

Next Steps:
1. Review the PR: {url}
2. Wait for CI checks
3. Request code review
4. Merge when approved
```

---

## Error Handling

### Artifact Not Found

```
Error: Investigation artifact not found.

Expected: .claude/PRPs/issues/issue-{number}.md

Did you investigate first?
Run: /prp-issue-investigate {number}
```

### Validation Failures

```
Validation Failed

{Which check failed}
{Error details}

The fix is incomplete. Please:
1. Review the error above
2. Fix the issue
3. Run validation again
4. Do not commit until all checks pass
```

### Archon Update Failed

```python
try:
    manage_task("update", task_id=task_id, status="done")
except Exception as e:
    log_warning(f"Archon update failed: {e}")
    log("Task status should be manually updated in Archon")
    # Continue - don't let Archon issues block completion
```

---

## Archon Task Lifecycle

```
Phase 1: LOAD
├── Task exists? → status: "doing"
└── No task? → Create with status: "doing"

Phase 4-5: IMPLEMENT & VERIFY
└── Task remains in "doing"

Phase 9: ARCHIVE
└── Task → status: "done"
```

---

## Quick Reference

| Phase | Action | Archon Status |
|-------|--------|---------------|
| 1. Load | Read artifact, start work | todo → doing |
| 2. Validate | Verify artifact currency | doing |
| 3. Git | Prepare branch | doing |
| 4. Implement | Execute each step | doing |
| 5. Verify | Run all validation | doing |
| 6. Commit | Create commit | doing |
| 7. PR | Push and create PR | doing |
| 8. Review | Self-review | doing |
| 9. Archive | Move artifact, complete | doing → done |
| 10. Report | Summary | done |
