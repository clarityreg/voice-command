---
description: Run CodeRabbit AI code review on your changes
argument-hint: [all|committed|uncommitted|branch:name]
---

# CodeRabbit Code Review

Run AI-powered code review using CodeRabbit CLI to catch issues before committing or creating a PR.

## Usage

```bash
/prp-coderabbit              # Review all changes (staged + unstaged)
/prp-coderabbit committed    # Review only committed changes
/prp-coderabbit uncommitted  # Review only uncommitted changes
/prp-coderabbit branch:main  # Compare current branch against main
```

---

## Phase 1: DETECT

Parse `$ARGUMENTS` to determine review scope:

| Input | Action |
|-------|--------|
| *(empty)* or `all` | Review all changes |
| `committed` | Review committed changes only |
| `uncommitted` | Review uncommitted changes only |
| `branch:<name>` | Compare against specified branch |
| `staged` | Review staged changes only |

---

## Phase 2: PRE-CHECK

Verify there are changes to review:

```bash
# Check for any changes
git status --porcelain

# Check for commits ahead of base
git log origin/main..HEAD --oneline 2>/dev/null
```

**If no changes**: Stop and inform user "No changes to review."

---

## Phase 3: RUN CODERABBIT

Execute the appropriate CodeRabbit command:

### All Changes (Default)
```bash
coderabbit review --plain --type all
```

### Committed Changes Only
```bash
coderabbit review --plain --type committed
```

### Uncommitted Changes Only
```bash
coderabbit review --plain --type uncommitted
```

### Compare Against Branch
```bash
coderabbit review --plain --base {branch-name}
```

### With Custom Config
```bash
coderabbit review --plain --config CLAUDE.md .coderabbit.yaml
```

---

## Phase 4: ANALYZE RESULTS

Parse CodeRabbit output and categorize findings:

### Severity Levels

| Level | Action Required |
|-------|-----------------|
| **Critical** | Must fix before merge - security vulnerabilities, data loss risks |
| **High** | Should fix - bugs, logic errors, race conditions |
| **Medium** | Consider fixing - code smells, performance issues |
| **Low** | Optional - style suggestions, minor improvements |

### Common Issues CodeRabbit Catches

- Race conditions
- Memory leaks
- Security vulnerabilities
- Missing error handling
- Logic gaps
- Missing tests
- AI hallucinations (when used with AI coding tools)

---

## Phase 5: REPORT

Output findings to user:

```
CodeRabbit Review Complete

Scope: {all|committed|uncommitted|branch comparison}
Files Reviewed: {count}

Issues Found:
- Critical: {count}
- High: {count}
- Medium: {count}
- Low: {count}

{If critical/high issues}
Action Required: Fix the following before proceeding:
{list of critical/high issues with file:line references}

{If only medium/low issues}
Suggestions (optional to address):
{list of suggestions}

{If no issues}
No issues found. Code looks good!

Next Steps:
{Based on findings - fix issues, or proceed to commit/PR}
```

---

## Integration with PRP Workflow

### Before Committing
```bash
# Review uncommitted changes
/prp-coderabbit uncommitted

# If clean, commit
/prp-commit
```

### Before Creating PR
```bash
# Review all changes against main
/prp-coderabbit branch:main

# If clean, create PR
/prp-pr
```

### After Implementation
```bash
# After /prp-implement completes
/prp-coderabbit committed

# Then run code-simplifier if needed
# Then create PR
```

---

## Quick Reference

| Command | What It Reviews |
|---------|-----------------|
| `coderabbit review --plain` | All changes |
| `coderabbit review --plain --type uncommitted` | Staged + unstaged |
| `coderabbit review --plain --type committed` | Committed only |
| `coderabbit review --plain --base main` | Branch diff vs main |
| `coderabbit review --prompt-only` | Minimal output for AI agents |

---

## Configuration

Create `.coderabbit.yaml` in project root for custom rules:

```yaml
language: en
reviews:
  path_filters:
    - "!**/*.test.ts"
    - "!**/node_modules/**"
  auto_review:
    enabled: true
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Rate limited | Wait or upgrade to Pro plan |
| Auth error | Run `coderabbit auth login` |
| No output | Check `git status` - may have no changes |
| Timeout | Try `--type uncommitted` for smaller scope |
