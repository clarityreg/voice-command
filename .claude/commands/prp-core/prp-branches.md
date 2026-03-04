---
description: Generate interactive branch/PR visualization
argument-hint: []
---

# Branch Visualization

Generate a self-contained dark-themed HTML page with a Mermaid.js gitgraph, branch table with PR status, ahead/behind counts, and optional Plane task creation.

## Usage

```bash
/prp-branches
```

---

## Phase 1: RUN SCRIPT

Execute the branch visualization script:

```bash
python3 scripts/branch-viz.py
```

**Requirements:**
- Must be run from the project root (where `.git/` lives)
- `gh` CLI optional — enables PR status badges (install: `brew install gh`)
- `.claude/prp-settings.json` optional — enables Plane task creation buttons
- Stdlib only — no pip installs needed

---

## Phase 2: WHAT THE SCRIPT COLLECTS

| Data | Source |
|------|--------|
| Branch list | `git branch` |
| Ahead/behind vs main | `git rev-list --left-right --count` |
| Last commit per branch | `git log --format=... -1 {branch}` |
| PR status (open/merged/closed/draft) | `gh pr list --json ...` |
| GitHub branch URLs | Derived from `git remote get-url origin` |
| Plane workspace config | `.claude/prp-settings.json` |

---

## Phase 3: OUTPUT FILE

The HTML is written to:

```
.claude/PRPs/branches/branch-viz.html
```

Then opened automatically in your default browser.

---

## Phase 4: REPORT

Tell the user:

```
Branch Visualization
====================
Branches:  8 local
Open PRs:  3
Plane:     configured (workspace: my-workspace)

Saved: .claude/PRPs/branches/branch-viz.html
Opened in browser.
```

---

## HTML Page Features

### Gitgraph (top section)
- Mermaid.js `gitGraph LR` diagram via CDN
- Shows last ~3 commits on main + diverging commits per feature branch
- Dark theme with color-coded branches

### Branch Table (bottom section)

| Column | Description |
|--------|-------------|
| Branch | Linked to GitHub branch page |
| PR Status | Colored badge (Open / Merged / Closed / Draft / No PR) |
| +Ahead / -Behind | Commits ahead and behind vs main |
| Last Commit | Commit message (truncated) |
| Hash · When | Short hash and relative time |
| Plane | "Create Plane Task" button (if configured) |

### Plane Integration

When `.claude/prp-settings.json` has `workspace_slug` and `project_id` set, each branch row shows a **"+ Plane"** button.

Clicking it **copies a pre-filled `curl` command** to your clipboard:

```bash
curl -X POST https://api.plane.so/api/v1/workspaces/{slug}/projects/{id}/issues/ \
  -H 'X-Api-Key: YOUR_PLANE_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"name": "[branch-name] ", "description": "Branch: ...", "priority": "medium"}'
```

Replace `YOUR_PLANE_API_KEY` with your actual key, then run the command in your terminal.

> The API key is intentionally **not** stored in the HTML — it's read from your environment at runtime.

---

## Integration with PRP Workflow

```bash
# Before creating a PR — see all branch states at a glance
/prp-branches

# Then create the PR
/prp-pr

# Or review first
/prp-coderabbit branch:main
/prp-pr
```

---

## Refreshing

The HTML is regenerated each time you run `/prp-branches`. Previous files are overwritten (single file, not timestamped).
