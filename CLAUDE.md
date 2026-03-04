




<!-- PRP-FRAMEWORK-START -->
# PRP Framework - Unified Agentic Engineering System

This is a unified PRP (Prompt Reference Protocol) framework that combines:
- **Wirasm's PRPs-agentic-eng**: Structured workflows for PRD→Plan→Implement
- **Your PRP-PACKAGE**: Archon MCP integration and shell-based Ralph loop

## Command Reference

All commands use the `/prp-*` namespace:

| Command | Purpose | Archon Integration |
|---------|---------|-------------------|
| `/prp-prd <description>` | Generate a Product Requirements Document | None |
| `/prp-plan <prd-or-description>` | Create implementation plan | Creates Archon project + tasks |
| `/prp-implement <plan-file>` | Execute implementation plan | Updates task statuses |
| `/prp-issue-investigate <issue>` | Investigate GitHub issue | Creates Archon task |
| `/prp-issue-fix <artifact>` | Fix from investigation artifact | Updates task to done |
| `/prp-debug <symptom>` | Root cause analysis | None |
| `/prp-review <PR>` | Code review a pull request | None |
| `/prp-commit [target]` | Smart git commit | None |
| `/prp-pr [base]` | Create pull request | None |
| `/prp-validate [scope]` | Run comprehensive validation | None |
| `/prp-explain <file-or-function>` | Explain code with control/data flow analysis | None |
| `/prp-test <file-or-description>` | Generate tests matching project conventions | None |
| `/prp-doctor` | Diagnose project health (env, structure, git) | Checks Plane status |
| `/prp-obsidian [content]` | Add a note to the Obsidian vault | None |
| `/prp-primer` | Load project context | Reports Archon status |
| `/prp-coderabbit [scope]` | Run CodeRabbit AI code review | None |
| `/prp-ci-init` | Initialize CI/CD workflows from templates | None |
| `/prp-coverage` | Run tests and generate coverage reports | None |
| `/prp-branches` | Interactive branch/PR visualization | None |
| `/prp-hookify` | Convert deterministic CLAUDE.md rules into enforced hooks | None |
| `/prp-claudemd` | Audit and optimize CLAUDE.md — move reference to docs/, prune unused | None |
| `/prp-transcript-audit` | Analyse transcripts for failure signals | Creates Plane review task |
| `/e2e-test` | Full E2E testing with agent-browser | Creates tasks per journey |
| `/agent-browser` | Browser automation reference (agent-browser CLI) | None |

## Project Settings

The framework uses `.claude/prp-settings.json` as a shared configuration file read by hooks, scripts, CI templates, and the TUI browser.

```json
{
  "project": {
    "name": "",
    "type": "",
    "backend_dir": "backend",
    "frontend_dir": "frontend"
  },
  "plane": {
    "workspace_slug": "",
    "project_id": "",
    "backlog_state_id": "",
    "api_url": "https://api.plane.so/api/v1"
  },
  "claude_secure_path": "",
  "coverage": {
    "targets": { "overall": 80, "critical": 90 }
  },
  "ci": {
    "use_npm_ci": true,
    "node_version": "20",
    "python_version": "3.12"
  }
}
```

- **Python hooks** use `.claude/hooks/prp_settings.py` (`load_settings()`, `get_plane_config()`)
- **Lua TUI** uses `config.load_prp_settings()` and `config.save_prp_settings()`
- **Plane API key** is always read from `.claude/prp-secrets.env` or `PLANE_API_KEY` env var — never stored in settings JSON
- **Template file**: `.claude/prp-settings.template.json` is copied on `setup-prp.sh` if no settings exist

## Archon MCP Integration

When Archon MCP is configured, the system provides:

1. **Task-Driven Development** - All work tracked through Archon tasks
2. **RAG Knowledge Search** - Query documentation before implementation
3. **Project Organization** - Features organized into projects
4. **Status Synchronization** - Task statuses are source of truth

### Archon Functions Used

```python
# Projects
find_projects(query="...")
manage_project("create"/"update"/"delete", ...)

# Tasks
find_tasks(filter_by="status"/"project", filter_value="...")
manage_task("create"/"update"/"delete", ...)

# RAG
rag_get_available_sources()
rag_search_knowledge_base(query="...")
rag_search_code_examples(query="...")
```

### Task Status Flow

```
todo → doing → review → done
```

- Only ONE task should be in "doing" status at a time
- Tasks move to "review" after implementation, before validation
- Tasks move to "done" after tests pass

## Ralph Loop (Autonomous Development)

The Ralph loop enables autonomous iterative development:

```bash
./ralph/loop.sh              # Run indefinitely (unified mode)
./ralph/loop.sh 10           # Run 10 iterations
./ralph/loop.sh plan 5       # Run 5 planning iterations
./ralph/loop.sh verify 3     # Run 3 verification iterations
```

### How it Works

1. Each iteration runs Claude with fresh context
2. `ralph/PROMPT_unified.md` provides instructions
3. `ralph/IMPLEMENTATION_PLAN.md` tracks progress
4. Git commits are made after each completed task
5. Changes are pushed automatically

### With Archon

When Archon is available, the Ralph loop:
- Syncs task statuses at start of each iteration
- Updates Archon when tasks complete
- Uses Archon as source of truth over file checkboxes

## Directory Structure

```
.claude/
├── commands/prp-core/       # PRP commands
│   ├── prp-prd.md
│   ├── prp-plan.md          # + Archon integration
│   ├── prp-implement.md     # + Archon integration
│   ├── prp-issue-investigate.md # + Archon task creation
│   ├── prp-issue-fix.md     # + Archon status updates
│   ├── prp-debug.md
│   ├── prp-review.md
│   ├── prp-commit.md
│   ├── prp-pr.md
│   ├── prp-validate.md
│   ├── prp-explain.md      # Code explanation with call/data flow
│   ├── prp-test.md         # Test scaffolding matching conventions
│   ├── prp-doctor.md       # Project health diagnostics
│   ├── prp-obsidian.md     # Add note to Obsidian vault
│   ├── prp-primer.md
│   ├── prp-coderabbit.md    # CodeRabbit AI review
│   ├── prp-ci-init.md       # Initialize CI/CD from templates
│   ├── prp-coverage.md      # Coverage report generation
│   ├── prp-branches.md      # Branch/PR visualization
│   ├── prp-hookify.md       # Convert CLAUDE.md rules to hooks
│   ├── prp-transcript-audit.md # Transcript failure-signal analysis
│   ├── e2e-test.md          # E2E testing with agent-browser
│   └── agent-browser.md     # Browser automation CLI reference
├── skills/                  # Auto-triggered skills (context-aware)
│   ├── prp-test-nudge/      # Detects missing test files
│   ├── prp-decision-capture/ # Captures architecture decisions to Obsidian
│   ├── prp-security-nudge/  # Flags security anti-patterns at write time
│   └── prp-context-enricher/ # Surfaces related context when entering a code area
├── agents/                  # Specialized agent prompts
│   └── code-simplifier.md   # Post-implementation simplification
├── scripts/                 # Git workflow hooks
│   ├── branch_guard.py      # Blocks changes on protected branches
│   ├── branch_naming.py     # Enforces branch naming conventions
│   ├── commit_scope.py      # Warns on mixed-concern commits
│   ├── prepush_checklist.py # Pre-push review checklist
│   └── session_context.py   # Injects git state on session start
├── hooks/                   # Automation hooks
│   ├── auto-format.sh       # Auto-format on Write/Edit
│   ├── auto_allow_readonly.py # PermissionRequest: auto-approves read-only ops
│   ├── backup_transcript.py # PreCompact: saves transcript before compaction
│   ├── log_failures.py      # PostToolUseFailure: logs failures + plays error sound
│   ├── status_line.py       # Status line: model, context %, branch, dirty, time
│   ├── prp_settings.py      # Shared settings loader (Python)
│   ├── generated/           # Auto-generated hooks from /prp-hookify
│   └── observability/       # Dashboard event forwarding
│       ├── __init__.py
│       ├── send_event.py    # HTTP POST to observability server
│       ├── model_extractor.py # Model name from transcript
│       └── constants.py     # Log directory config
├── templates/ci/            # CI workflow templates
│   ├── ci.yml.template
│   ├── deploy.yml.template
│   └── electron-release.yml.template
├── prp-settings.json        # Shared project settings
├── prp-settings.template.json # Settings template (copied on setup)
├── PRPs/                    # Artifact storage
│   ├── prds/               # PRD documents
│   ├── plans/              # Implementation plans
│   ├── issues/             # Issue investigations
│   ├── reviews/            # PR reviews
│   ├── coverage/           # Coverage reports (gitignored)
│   ├── branches/           # Branch visualizations (gitignored)
│   └── transcript-analysis/ # Transcript analysis reports (gitignored)
└── settings.json           # Hook configuration

apps/                        # Observability dashboard
├── server/                 # Bun + SQLite event store (port 4000)
└── client/                 # Vue + Vite dashboard (port 5183)

scripts/                     # Pre-commit supporting scripts
├── lint-frontend.sh        # ESLint wrapper for frontend
├── check-file-size.sh      # Python file size enforcement
├── trivy-precommit.sh      # Trivy security scan + reporting
├── coverage-report.sh      # Test coverage report generator
├── branch-viz.py           # Branch/PR visualization HTML
├── transcript-analyser.py  # Transcript failure-signal mining
├── transcript-analyser-template.html # Analyser report template
├── reports-hub.py          # Unified reports index page
├── reports-hub-template.html # Reports hub template
├── start-observability.sh  # Start dashboard server + client
└── stop-observability.sh   # Stop dashboard processes

ralph/                       # Ralph autonomous loop
├── loop.sh                 # Main loop script
├── PROMPT_unified.md       # + Archon sync
├── PROMPT_plan.md
├── PROMPT_verify.md
├── AGENTS.md
└── IMPLEMENTATION_PLAN.md

.pre-commit-config.yaml      # Pre-commit hook configuration
.gitignore                   # Git ignore rules
```

## Fallback Behavior

All commands gracefully handle missing Archon:

1. Log warning: "Archon not configured, using file-based tracking"
2. Skip Archon-specific phases
3. Continue with file-based state management
4. All workflows remain fully functional

## Quick Start

### New Feature Development

```bash
# 1. Create PRD
/prp-prd My new feature description

# 2. Generate implementation plan (creates Archon project)
/prp-plan .claude/PRPs/prds/my-new-feature.prd.md

# 3. Implement (updates Archon tasks)
/prp-implement .claude/PRPs/plans/my-new-feature.plan.md

# 4. Validate
/prp-validate

# 5. AI Code Review (before PR)
/prp-coderabbit branch:main

# 6. Create PR
/prp-pr
```

### Bug Fix Workflow

```bash
# 1. Investigate issue (creates Archon task)
/prp-issue-investigate #123

# 2. Fix (updates Archon task to done)
/prp-issue-fix .claude/PRPs/issues/issue-123.md
```

### Autonomous Development

```bash
# Run Ralph loop for autonomous implementation
./ralph/loop.sh 5
```

## Pre-commit Hooks

The framework includes a `.pre-commit-config.yaml` with 16 hooks in execution order:

| Hook | Scope | Blocking |
|------|-------|----------|
| `ruff` (lint + fix) | `backend/`, `tests/` | Yes |
| `ruff-format` | `backend/`, `tests/` | Yes |
| `vulture` (dead code) | `backend/` | Yes |
| `bandit` (security) | `backend/` | Yes |
| `eslint-frontend` | `frontend/**/*.{ts,tsx}` | Yes |
| `python-file-size` (< 500 lines) | `backend/**/*.py` | Yes |
| `detect-secrets` | All (excl. `.lock`, `.min.js`) | Yes |
| `trivy-scan` | All staged files | CRITICAL only |
| `coderabbit-review` | All staged files | No (advisory) |
| `trailing-whitespace` | All | Yes (auto-fix) |
| `end-of-file-fixer` | All | Yes (auto-fix) |
| `check-yaml` | `*.yaml` | Yes |
| `check-added-large-files` (> 1MB) | All (excl. `.icns`) | Yes |
| `check-merge-conflict` | All | Yes |
| `detect-private-key` | All | Yes |

### Skipping Hooks

```bash
SKIP=coderabbit-review git commit -m "quick fix"
SKIP=coderabbit-review,trivy-scan git commit -m "skip slow hooks"
```

### Project-Specific Hooks

Hooks scoped to `backend/` or `frontend/` only run when those directories exist.
Configure tool settings in `pyproject.toml` (ruff, bandit) and `.coderabbit.yaml`.

## Auto-Triggered Skills

Skills are context-aware behaviors that Claude activates automatically — no `/command` needed. They complement commands (explicit) and hooks (mechanical) with intelligent, advisory nudges.

| Skill | Category | Trigger | Action |
|-------|----------|---------|--------|
| `checking-test-coverage-gaps` | Guardrail | Source file edited with no test counterpart | Suggests `/prp-test <file>` |
| `capturing-architecture-decisions` | Knowledge | New endpoint, migration, dependency, or service added | Offers to write ADR to Obsidian |
| `detecting-security-antipatterns` | Guardrail | Code with hardcoded secrets, SQL injection, eval, etc. | Flags with severity + fix |
| `enriching-session-context` | Context | User starts working on a new code area | Surfaces related Obsidian notes, PRPs, coverage, Plane tasks |
| `checking-framework-sync` | Guardrail | PRP framework source file modified (command, hook, script, settings) | Checks if Obsidian, nvim plugin, install script, CLAUDE.md need updating; asks user to confirm |

**Design principles:**
- **Advisory only** — skills never block or auto-execute. They suggest; the user decides.
- **Once per topic** — no repeated nudges for the same file/area in a session.
- **Complement hooks** — security skill catches issues at write time; pre-commit hooks catch at commit time.

Skill definitions live in `.claude/skills/<skill-name>/SKILL.md`.

## Observability Dashboard

Real-time visualization of all Claude Code hook events via a Bun+SQLite server and Vue dashboard.

### Startup

```bash
./scripts/start-observability.sh   # Start server (port 4000) + client (port 5183)
./scripts/stop-observability.sh    # Stop both
```

- Dashboard: `http://localhost:5183`
- Server API: `http://localhost:4000`
- Health check: `http://localhost:4000/health`

### How it Works

Every hook event in `settings.json` has a secondary command that forwards the event JSON to the observability server via `.claude/hooks/observability/send_event.py`. This is **best-effort** — if the server isn't running, `send_event.py` exits silently (exit 0) and PRP hooks continue normally.

### `--source-app` Pattern

Each project identifies itself via `--source-app <name>`. PRP uses `--source-app prp-framework`. Future integrations (security tool, visualiser, test runner) will use their own names to appear as separate swim lanes in the dashboard.

### Architecture

```
.claude/hooks/observability/
├── __init__.py           # Package marker
├── send_event.py         # HTTP POST to localhost:4000/events
├── model_extractor.py    # Extracts model name from transcript
├── constants.py          # Log directory configuration
└── logs/                 # Session logs (gitignored)

apps/
├── server/               # Bun + SQLite event store
│   └── src/              # TypeScript server (port 4000)
└── client/               # Vue + Vite dashboard
    └── src/              # TypeScript frontend (port 5183)
```

### Events Tracked

| Event | PRP Hook | Observability |
|-------|----------|---------------|
| `SessionStart` | session_context.py, hook_handler.py | send_event.py |
| `PreToolUse` | branch_guard.py, hook_handler.py | send_event.py |
| `PostToolUse` | hook_handler.py | send_event.py |
| `Stop` | hook_handler.py | send_event.py (+ `--add-chat`) |
| `Notification` | hook_handler.py | send_event.py |
| `SubagentStop` | hook_handler.py | send_event.py |
| `PermissionRequest` | auto_allow_readonly.py | send_event.py |
| `PreCompact` | backup_transcript.py | send_event.py |
| `PostToolUseFailure` | log_failures.py | send_event.py |
| `UserPromptSubmit` | — | send_event.py |
| `SubagentStart` | — | send_event.py |
| `SessionEnd` | — | send_event.py |

## Key Principles

1. **Archon First** - When available, Archon is the source of truth for task state
2. **Validation Always** - Run checks after every change
3. **Tests Required** - No task complete without passing tests
4. **Document Everything** - Plans, investigations, and reviews are saved as artifacts
5. **Graceful Fallback** - System works with or without Archon
<!-- PRP-FRAMEWORK-END -->
