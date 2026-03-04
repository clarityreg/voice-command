---
description: Create a git commit using natural language file targeting
argument-hint: [file-pattern or description]
---

# Smart Git Commit

A streamlined commit workflow that interprets natural language to stage specific files and generate conventional commit messages.

---

## Phase 1: ASSESS

Check for changes:

```bash
git status --short
```

**If no changes**: Stop and inform user "No changes to commit."

**If changes exist**: Proceed to Phase 2.

---

## Phase 2: INTERPRET & STAGE

Parse `$ARGUMENTS` to determine what to stage:

### Input Patterns

| Input | Action |
|-------|--------|
| *(empty)* | Stage all changes (`git add -A`) |
| `staged` | Use currently staged files (no additional staging) |
| `*.ts` or `typescript files` | Stage matching pattern |
| `src/` or `the src folder` | Stage directory |
| `except package-lock` | Stage all EXCEPT matches |
| `only new files` | Stage only untracked files |
| `only modified` | Stage only modified files |

### Staging Commands

```bash
# All changes
git add -A

# Pattern matching
git add "*.ts"
git add "*.{ts,tsx}"

# Directory
git add src/

# Except (add all, then unstage)
git add -A
git reset -- package-lock.json

# Only untracked
git add $(git ls-files --others --exclude-standard)

# Only modified (not new)
git add -u
```

### Verify Staging

```bash
git diff --staged --name-only
```

Report what will be committed.

---

## Phase 3: COMMIT

### Analyze Changes

Review the staged diff to understand:
- What type of change is this?
- What's the main purpose?
- Any breaking changes?

### Generate Message

Use conventional commit format:

```
{type}: {description}
```

**Types:**
| Type | When to Use |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code change without feature/fix |
| `docs` | Documentation only |
| `test` | Adding/updating tests |
| `chore` | Build, config, dependencies |
| `style` | Formatting, no code change |
| `perf` | Performance improvement |

**Message Rules:**
- First line under 72 characters
- Use imperative mood ("add" not "added")
- No period at the end
- Describe the "what" not the "how"

### Create Commit

```bash
git commit -m "{type}: {description}"
```

For longer messages with body:

```bash
git commit -m "{type}: {description}

{optional body with more details}

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 4: OUTPUT

Report to user:

```
Commit Created

Hash: {short-hash}
Message: {commit message}
Files: {count} file(s) changed

Changes:
+ {additions} insertions
- {deletions} deletions

Next Steps:
- Push to remote: git push
- Create PR: /prp-pr
- Continue working: {suggestion based on context}
```

---

## Examples

### Stage and commit all
```
User: /prp-commit
Action: git add -A && git commit -m "feat: add user authentication"
```

### Commit specific files
```
User: /prp-commit the typescript files
Action: git add "*.ts" "*.tsx" && git commit -m "refactor: update type definitions"
```

### Commit with exclusion
```
User: /prp-commit except the lock files
Action: git add -A && git reset -- "*.lock" "*-lock.json" && git commit -m "chore: update dependencies"
```

### Only staged files
```
User: /prp-commit staged
Action: git commit -m "fix: resolve null pointer in user service"
```

---

## Error Handling

### Nothing Staged
```
No files staged for commit.

Did you mean to:
1. Stage all changes? Run: /prp-commit
2. Stage specific files? Run: /prp-commit <pattern>
```

### Commit Hooks Failed
```
Commit rejected by pre-commit hook.

Hook output:
{error message}

To fix:
1. Address the issues above
2. Try committing again: /prp-commit
```

### Merge Conflict
```
Cannot commit - merge conflicts detected.

Conflicting files:
{file list}

To fix:
1. Resolve conflicts in each file
2. Stage resolved files: git add <file>
3. Complete merge: git commit
```
