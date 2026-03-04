---
description: Create a pull request from the current branch
argument-hint: [target-branch]
---

# Pull Request Creator

Create a well-documented pull request from your current branch using the `gh` CLI tool.

---

## Phase 1: VALIDATE

### Check Prerequisites

```bash
# Get current branch
CURRENT_BRANCH=$(git branch --show-current)

# Verify not on main/master
if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" ]]; then
    echo "Cannot create PR from main/master branch"
    exit 1
fi

# Check for uncommitted changes
git status --porcelain
```

**If uncommitted changes exist**: Warn user and suggest `/prp-commit` first.

### Verify Commits Exist

```bash
# Check commits ahead of base
git log origin/{base}..HEAD --oneline
```

**If no commits**: Stop and inform user.

### Check for Existing PR

```bash
gh pr list --head "$CURRENT_BRANCH" --json number,url
```

**If PR exists**: Report existing PR URL instead of creating new.

---

## Phase 2: DISCOVER

### Locate PR Templates

```bash
# Check common template locations
ls .github/PULL_REQUEST_TEMPLATE.md 2>/dev/null
ls .github/PULL_REQUEST_TEMPLATE/ 2>/dev/null
ls docs/PULL_REQUEST_TEMPLATE.md 2>/dev/null
```

### Analyze Commits

```bash
# Get commit messages for context
git log origin/{base}..HEAD --format="%s%n%b"
```

### Examine Changed Files

```bash
# List all changed files
git diff origin/{base}..HEAD --name-only

# Get stats
git diff origin/{base}..HEAD --stat
```

### Determine PR Title

Use conventional commit prefix based on changes:

| Change Type | Prefix |
|-------------|--------|
| New feature | `feat:` |
| Bug fix | `fix:` |
| Refactor | `refactor:` |
| Documentation | `docs:` |
| Tests | `test:` |
| Build/config | `chore:` |

Generate title from:
1. Most significant commit message, OR
2. Summary of all changes

---

## Phase 3: PUSH

Ensure branch exists on remote:

```bash
git push -u origin "$CURRENT_BRANCH"
```

---

## Phase 4: CREATE

### Build PR Body

If template exists, fill it in. Otherwise use default format:

```markdown
## Summary

{2-3 bullet points describing the changes}

## Changes

{Categorized list of changes}

### Added
- {new feature/file}

### Changed
- {modified behavior/file}

### Fixed
- {bug fix}

### Removed
- {deleted feature/file}

## Files Modified

{List of key files changed with brief description}

## Testing

- [ ] Unit tests added/updated
- [ ] Manual testing completed
- [ ] Build passes locally

## Related Issues

{Link to related issues: Closes #123, Relates to #456}

---
*Created with Claude Code*
```

### Create the PR

```bash
# Determine base branch (from $ARGUMENTS or default)
BASE_BRANCH=${ARGUMENTS:-main}

# Create PR
gh pr create \
    --base "$BASE_BRANCH" \
    --title "{title}" \
    --body "{body}"
```

For draft PRs:
```bash
gh pr create --draft --base "$BASE_BRANCH" --title "{title}" --body "{body}"
```

---

## Phase 5: VERIFY

### Confirm Creation

```bash
# Get PR details
gh pr view --json number,url,title,state
```

### Check CI Status

```bash
# Wait briefly for CI to start
sleep 5

# Check status
gh pr checks
```

---

## Phase 6: OUTPUT

Report to user:

```
Pull Request Created

PR: #{number}
URL: {url}
Title: {title}
Base: {base} <- {head}

Files Changed: {count}
  + {additions} additions
  - {deletions} deletions

CI Status: {Pending | Running | Passed | Failed}

Next Steps:
1. Review the PR: {url}
2. Monitor CI checks
3. Request reviewers if needed: gh pr edit --add-reviewer @username
4. After approval, merge: gh pr merge --squash
```

---

## Edge Cases

### Diverged Branch

If branch has diverged from base:

```
Warning: Your branch has diverged from {base}.

Options:
1. Rebase: git rebase origin/{base}
2. Merge: git merge origin/{base}
3. Create PR anyway (may have conflicts)

Recommendation: Rebase first for cleaner history.
```

### No Upstream Set

```bash
git push -u origin "$CURRENT_BRANCH"
```

### Large PR Warning

If more than 500 lines changed:

```
Note: This is a large PR ({lines} lines changed).

Consider:
- Breaking into smaller PRs if possible
- Adding extra context in description
- Requesting multiple reviewers
```

---

## PR Best Practices

### Good PR Characteristics
- Single responsibility (one feature/fix)
- Under 400 lines when possible
- Clear title and description
- Tests included
- Documentation updated

### Title Format
```
{type}: {concise description}

Examples:
feat: add user authentication flow
fix: resolve race condition in data loader
refactor: extract validation logic to shared module
```

### Linking Issues
```markdown
Closes #123
Fixes #456
Relates to #789
```
