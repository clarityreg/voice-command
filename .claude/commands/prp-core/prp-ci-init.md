---
description: Initialize CI/CD workflow files from templates
argument-hint: [--force]
---

# Initialize CI/CD Workflows

Generate GitHub Actions workflow files from the PRP framework templates, with values filled from `.claude/prp-settings.json`.

## Phase 1: READ SETTINGS

Read `.claude/prp-settings.json` and extract:

```
python_version   ← ci.python_version (default: "3.12")
node_version     ← ci.node_version (default: "20")
coverage_overall ← coverage.targets.overall (default: 80)
backend_dir      ← project.backend_dir (default: "backend")
frontend_dir     ← project.frontend_dir (default: "frontend")
use_npm_ci       ← ci.use_npm_ci (default: true)
project_type     ← project.type (e.g., "fullstack", "backend", "frontend", "electron")
```

Derive:
- `npm_install_command` = `"npm ci"` if `use_npm_ci` is true, else `"npm install"`

---

## Phase 2: READ TEMPLATES

Read templates from `.claude/templates/ci/`:

| Template | Output | When to skip |
|----------|--------|-------------|
| `ci.yml.template` | `.github/workflows/ci.yml` | Never (always generate) |
| `deploy.yml.template` | `.github/workflows/deploy.yml` | Never (always generate) |
| `electron-release.yml.template` | `.github/workflows/electron-release.yml` | Skip unless `project.type` contains "electron" |

---

## Phase 3: REPLACE PLACEHOLDERS

For each template, replace all `{{placeholder}}` occurrences:

| Placeholder | Value |
|------------|-------|
| `{{python_version}}` | ci.python_version |
| `{{node_version}}` | ci.node_version |
| `{{coverage_overall}}` | coverage.targets.overall |
| `{{backend_dir}}` | project.backend_dir |
| `{{frontend_dir}}` | project.frontend_dir |
| `{{npm_install_command}}` | "npm ci" or "npm install" |

---

## Phase 4: WRITE WORKFLOWS

1. Create `.github/workflows/` directory if it doesn't exist
2. Write each generated workflow file
3. If `--force` is NOT passed and files already exist, warn and ask before overwriting

---

## Phase 5: REPORT

```
CI/CD Workflows Generated
=========================
  ✓ .github/workflows/ci.yml
  ✓ .github/workflows/deploy.yml
  ⊘ .github/workflows/electron-release.yml (skipped — not electron project)

Settings used:
  Python:   3.12
  Node:     20
  Coverage: 80%
  Backend:  backend/
  Frontend: frontend/
  Install:  npm ci

Next: Review the generated workflows and customize deploy steps.
```

---

## Notes

- The CI template uses `dorny/paths-filter` so backend/frontend jobs only run when their code changes
- The deploy template has placeholder deploy steps marked with `# TODO` — customize for your hosting provider
- The electron template creates draft GitHub Releases — publish manually after testing
- Re-run `/prp-ci-init --force` after changing settings to regenerate workflows
