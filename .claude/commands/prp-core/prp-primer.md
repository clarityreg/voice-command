---
description: Prime context for the AI coding assistant - catch up on the project
---

# Project Context Primer

Use this command to quickly catch up on a project's context when starting a new conversation or switching projects.

---

## Phase 1: Project Documentation

### 1.1 Read Core Documentation

Start by reading key project files:

```
1. CLAUDE.md (if exists) - Project-specific AI instructions
2. README.md - Project overview and setup
3. CONTRIBUTING.md (if exists) - Contribution guidelines
4. docs/ folder (if exists) - Additional documentation
5. .claude/docs/ folder (if exists) - PRP reference documentation
```

### 1.2 Check for PRP Artifacts

```bash
# Check for existing PRPs
ls -la .claude/PRPs/ 2>/dev/null

# Check for active plans
ls -la .claude/PRPs/plans/ 2>/dev/null

# Check for pending issues
ls -la .claude/PRPs/issues/ 2>/dev/null
```

---

## Phase 2: Archon Context (if available)

**Check for existing Archon projects:**

```python
# 1. List all projects
projects = find_projects()

# 2. Report active work
for project in projects:
    tasks = find_tasks(filter_by="project", filter_value=project["id"])

    doing_tasks = [t for t in tasks if t["status"] == "doing"]
    todo_tasks = [t for t in tasks if t["status"] == "todo"]

    if doing_tasks or todo_tasks:
        print(f"Project: {project['title']}")
        print(f"  In Progress: {len(doing_tasks)}")
        print(f"  Pending: {len(todo_tasks)}")
```

**If active tasks found:**
- Report current work in progress
- Note any blockers
- Suggest resuming with `/prp-implement` or relevant command

---

## Phase 3: Codebase Structure

### 3.1 Identify Project Type

```bash
# Package managers and build tools
ls package.json pyproject.toml Cargo.toml go.mod Makefile 2>/dev/null

# Framework indicators
ls manage.py next.config.js vite.config.ts angular.json 2>/dev/null
```

### 3.2 Read Key Directories

**For a typical full-stack project:**

```
Backend:
- backend/ or src/ - Main application code
- apps/ or modules/ - Feature modules
- config/ or settings/ - Configuration
- tests/ - Test files

Frontend:
- frontend/ or client/ - Frontend code
- src/components/ - UI components
- src/pages/ or app/ - Pages/routes
- src/lib/ or src/utils/ - Utilities
```

### 3.3 Sample Key Files

Read a few representative files from each major area to understand patterns:
- A model/entity file
- A controller/view file
- A component file
- A test file

---

## Phase 4: Dependencies and Configuration

### 4.1 Dependencies

```bash
# Node/JavaScript
cat package.json | jq '.dependencies, .devDependencies'

# Python
cat pyproject.toml 2>/dev/null || cat requirements.txt 2>/dev/null

# Rust
cat Cargo.toml

# Go
cat go.mod
```

### 4.2 Configuration Files

Look for:
- Environment configuration (`.env.example`, `config/`)
- Build configuration (`webpack.config.js`, `tsconfig.json`, etc.)
- CI/CD configuration (`.github/workflows/`, `.gitlab-ci.yml`)
- Docker configuration (`Dockerfile`, `docker-compose.yml`)

---

## Phase 5: Generate Summary

Explain back to the user:

```markdown
# Project Summary: {Project Name}

## Overview
{Brief description from README}

## Project Structure

### Backend
- **Framework**: {Django/FastAPI/Express/etc.}
- **Language**: {Python/TypeScript/Go/etc.}
- **Key Directories**:
  - `{path}` - {purpose}

### Frontend
- **Framework**: {React/Vue/Next.js/etc.}
- **Key Directories**:
  - `{path}` - {purpose}

### Database
- **Type**: {PostgreSQL/MongoDB/etc.}
- **ORM**: {Django ORM/Prisma/SQLAlchemy/etc.}

## Key Files

| File | Purpose |
|------|---------|
| `{path}` | {description} |

## Dependencies

### Core
- {dependency 1} - {purpose}
- {dependency 2} - {purpose}

### Development
- {dev dependency} - {purpose}

## Configuration

- **Environment**: {.env setup notes}
- **Build**: {build tool notes}
- **Deployment**: {deployment notes}

## Active Work (from Archon)

{If Archon projects found}
- **Project**: {name}
  - In Progress: {count} tasks
  - Pending: {count} tasks

## PRP Artifacts

{If PRPs found}
- Active Plans: {count}
- Pending Issues: {count}

## Important Patterns

### Naming Conventions
- {pattern observation}

### Code Style
- {style observation}

### Testing
- {test pattern observation}

## Quick Start

To continue working on this project:
1. {setup step if needed}
2. {relevant /prp-* command suggestion}
```

---

## Output

Report to user:

```
Project Context Loaded

Project: {name}
Type: {backend/frontend/fullstack}
Stack: {languages and frameworks}

Key Findings:
- {finding 1}
- {finding 2}
- {finding 3}

Archon Status:
- Projects: {count or "Not configured"}
- Active Tasks: {count or "N/A"}

PRP Artifacts:
- Plans: {count}
- Issues: {count}

Recommendations:
{Based on what was found, suggest next steps}

I'm now ready to help with this project. What would you like to work on?
```

---

## Quick Reference

After priming, you'll understand:

1. **What the project does** - From README/docs
2. **How it's structured** - Directory layout
3. **What patterns to follow** - From existing code
4. **What's in progress** - From Archon/PRPs
5. **How to run/test** - From config files
6. **Key dependencies** - From package files

---

## When to Use

Use `/prp-primer` when:
- Starting a new conversation on an existing project
- Switching between projects
- Coming back to a project after time away
- Onboarding to a new codebase
- Before starting significant new work
