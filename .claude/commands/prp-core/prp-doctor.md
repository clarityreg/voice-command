---
description: Diagnose project health — environment, structure, code quality, and git status
argument-hint:
---

# Project Health Check

Run a comprehensive diagnostic of the project and report results as a checklist with pass/warn/fail per item.

---

## CRITICAL: Execution Rules

**Every check MUST be independent.** A failure in one check must NEVER affect another.

1. **Never chain checks with `&&`** — use `;` or run them as separate statements so a non-zero exit doesn't kill subsequent checks
2. **Never run check groups as parallel sibling Bash calls** — run ALL checks in a SINGLE Bash call per group, using `;` to separate commands, so one exit code 127 (command not found) doesn't cascade-cancel the other groups
3. **Always append `2>/dev/null || true`** to commands that might not exist (pre-commit, trivy, ruff) to guarantee exit 0
4. **Collect results, then report** — don't bail out mid-check

---

## Check Group 1: ENVIRONMENT

Verify required tools are installed and configured. Run ALL of these in a **single Bash call**, separated by `;` — never `&&`:

```bash
echo "PYTHON: $(python3 --version 2>&1 || echo 'NOT FOUND')" ;
echo "NODE: $(node --version 2>&1 || echo 'NOT FOUND')" ;
echo "GH: $(gh auth status 2>&1 || echo 'NOT FOUND')" ;
echo "PRECOMMIT: $(pre-commit --version 2>&1 || echo 'NOT FOUND')" ;
echo "PRECOMMIT_HOOK: $([ -f .git/hooks/pre-commit ] && echo 'installed' || echo 'not installed')" ;
echo "RUFF: $(ruff --version 2>&1 || echo 'NOT FOUND')" ;
echo "TRIVY: $(trivy --version 2>&1 | head -1 || echo 'NOT FOUND')"
```

Read `.claude/prp-settings.json` to get expected versions:
- Compare installed Python version against `ci.python_version`
- Compare installed Node version against `ci.node_version`

Report:
- PASS: tool installed and version matches (or no version constraint)
- WARN: tool installed but version mismatch
- FAIL: tool not installed

---

## Check Group 2: PROJECT STRUCTURE

Verify essential files and directories exist. Run in a **single Bash call**:

1. **`.env`** — If `.env.example` exists, check that `.env` also exists and contains all the same keys (values can differ). Report missing keys.
2. **`.claude/prp-settings.json`** — Exists and has a non-empty `project.name`
3. **Backend directory** — Check `project.backend_dir` from settings (default `backend/`). PASS if exists, WARN if setting is configured but dir is missing, SKIP if not configured.
4. **Frontend directory** — Same logic for `project.frontend_dir` (default `frontend/`).
5. **Test directory** — Search for `tests/`, `test/`, `__tests__/`, or `*.test.*` files. PASS if found, WARN if not.
6. **README.md** — Exists and is non-empty.

---

## Check Group 3: CODE HEALTH

Assess code quality signals. Run in a **single Bash call**:

1. **Oversized Python files** — Find `.py` files over 500 lines:
   ```bash
   find . -name "*.py" -not -path "*/node_modules/*" -not -path "*/.venv/*" -not -path "*/migrations/*" 2>/dev/null | while read f; do
     lines=$(wc -l < "$f")
     [ "$lines" -gt 500 ] && echo "WARN: $f ($lines lines)"
   done
   ```
   PASS: none found. WARN: list the offenders with line counts.

2. **TODO/FIXME count** — Non-blocking, just report:
   ```bash
   grep -rn "TODO\|FIXME\|HACK\|XXX" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" --include="*.rs" --include="*.go" . 2>/dev/null | grep -v node_modules | grep -v .venv | wc -l
   ```
   Report count. No pass/fail — purely informational.

3. **Coverage** — Check if `.claude/PRPs/coverage/latest.json` exists. If yes, read `overall_coverage` and compare against `coverage.targets.overall` from settings. PASS if meets target, WARN if below.

4. **Merge conflict markers** — Search tracked files for `<<<<<<<`, `=======`, `>>>>>>>`:
   ```bash
   git grep -l "<<<<<<< \|======= \|>>>>>>> " -- ':!*.md' 2>/dev/null || true
   ```
   PASS: none found. FAIL: list files with unresolved conflicts.

---

## Check Group 4: GIT HEALTH

Assess repository state. Run in a **single Bash call**:

1. **Protected branch** — Check if current branch is `main` or `master`. WARN if so (you should be on a feature branch).
2. **Uncommitted changes** — Run `git status --porcelain`. PASS if clean, WARN with count of modified/untracked files.
3. **Stale branches** — Find branches already merged into main but not deleted:
   ```bash
   git branch --merged main 2>/dev/null | grep -v "main\|master\|\*" | wc -l
   ```
   PASS: none. WARN: list them with suggestion to delete.
4. **Remote** — Verify remote is set and reachable:
   ```bash
   git remote get-url origin 2>/dev/null ; git ls-remote --exit-code origin HEAD 2>/dev/null || true
   ```
   PASS: remote set and reachable. FAIL: no remote or unreachable.

---

## Check Group 5: PLANE / ARCHON (conditional)

Only run if `.claude/prp-settings.json` has `plane.workspace_slug` and `plane.project_id` set.

1. **Plane API reachable** — Use `PLANE_API_KEY` from env or `.claude/prp-secrets.env`:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" \
     -H "X-API-Key: $PLANE_API_KEY" \
     "${PLANE_API_URL}/workspaces/${WORKSPACE_SLUG}/projects/${PROJECT_ID}/"
   ```
   PASS: 200. FAIL: any other status.

2. **Project ID valid** — Same call, check response has a valid project name.

3. **Tasks in "doing"** — Query Plane for in-progress tasks. Report count.
   PASS: 0 or 1. WARN: more than 1 (only one task should be in-progress at a time).

If Plane is not configured, SKIP this entire group.

---

## Check Group 6: PRP COMPONENTS

Verify PRP framework components are installed in the project. Run in a **single Bash call**:

Check for the presence of each component's files/directories:

1. **Core commands** — `.claude/commands/prp-core/` exists and has files
2. **Hook scripts** — `.claude/hooks/` exists
3. **Git guard scripts** — `.claude/scripts/` exists
4. **Skills** — `.claude/skills/` exists
5. **Agents** — `.claude/agents/` exists
6. **CI templates** — `.claude/templates/ci/` exists
7. **Pre-commit config** — `.pre-commit-config.yaml` exists
8. **Settings wiring** — `.claude/settings.json` exists
9. **Observability dashboard** — `apps/server/` exists
10. **Ralph loop** — `ralph/` exists

Report:
- PASS: component directory/file exists (include file count for directories)
- WARN: component not found (suggest running `install-prp.sh`)

---

## Check Group 7: QA INFRASTRUCTURE

Verify QA tooling is set up. Run in a **single Bash call**:

1. **QA directory** — `.claude/PRPs/qa/` exists. PASS if yes, WARN if not.
2. **Test results CSV** — Check path from `qa.tracking_csv` in settings (default `.claude/PRPs/qa/test-results.csv`). PASS if exists.
3. **Quality gates** — `qa.quality_gates` is configured in prp-settings.json. PASS if present with values.
4. **QA gate script** — `scripts/qa-gate-check.sh` exists. PASS if yes, SKIP if not (optional).

---

## Check Group 8: CI/CD CONFIGURED

Verify CI/CD workflows are set up. Run in a **single Bash call**:

1. **CI workflow** — `.github/workflows/ci.yml` exists. PASS if yes, WARN if not.
2. **Deploy workflow** — `.github/workflows/deploy.yml` exists. PASS if yes, SKIP if not (optional).
3. **CI templates** — `.claude/templates/ci/` directory exists with template files. PASS if yes, WARN if not.

---

## Check Group 9: OBSERVABILITY

Check if the observability dashboard is installed and running. Run in a **single Bash call**:

1. **Dashboard files** — `apps/server/` and `apps/client/` directories exist. PASS if yes, WARN if not.
2. **Observability server** — Only check if dashboard files exist. `curl -s --connect-timeout 2 http://localhost:4000/health 2>/dev/null || true`. PASS if HTTP 200, WARN if not running.

---

## Output Format

Present results as a clean checklist:

```
Project Health Check
====================

Environment
  PASS  Python 3.12.1 (expected: 3.12)
  PASS  Node 20.11.0 (expected: 20)
  PASS  gh CLI authenticated as @username
  WARN  pre-commit installed but hooks not set up
        -> Fix: run `pre-commit install`
  PASS  ruff 0.4.1
  SKIP  trivy not installed (optional)

Project Structure
  PASS  .env exists, all keys from .env.example present
  PASS  .claude/prp-settings.json configured (project: "my-app")
  PASS  backend/ directory exists
  PASS  frontend/ directory exists
  PASS  tests/ directory exists
  PASS  README.md exists (42 lines)

Code Health
  WARN  2 Python files over 500 lines
        -> backend/apps/auth/views.py (612 lines)
        -> backend/apps/api/serializers.py (534 lines)
  INFO  14 TODO/FIXME markers found
  PASS  Coverage: 83.2% (target: 80%)
  PASS  No merge conflict markers

Git Health
  PASS  On branch feature/my-feature (not protected)
  WARN  3 uncommitted changes
  WARN  2 stale branches (merged but not deleted)
        -> feature/old-thing, fix/typo
        -> Fix: git branch -d feature/old-thing fix/typo
  PASS  Remote: origin -> git@github.com:user/repo.git (reachable)

Plane Integration
  PASS  API reachable
  PASS  Project "my-app" found
  PASS  1 task in "doing" status

Score: 14/16 checks pass, 2 warnings
```

For every WARN or FAIL item, include a one-line actionable fix suggestion (prefixed with `-> Fix:`).

End with a summary score: `X/Y checks pass, Z warnings, W failures`.

---

## Phase 6: HTML REPORT

After displaying the console output above, generate a persistent HTML report:

```bash
python3 scripts/doctor-report.py
```

This runs the same checks programmatically and:
1. Generates a styled HTML report at `.claude/PRPs/doctor/doctor-report.html`
2. Opens it in the default browser

Report the saved file path to the user:
```
HTML report saved: .claude/PRPs/doctor/doctor-report.html
```
