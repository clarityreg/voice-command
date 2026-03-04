---
description: Run comprehensive validation across the entire project
argument-hint: [scope: all|backend|frontend|quick]
---

# Comprehensive Project Validation

Validate the entire project across code quality, type safety, testing, and integration workflows.

## Overview

This validation command performs a multi-phase check across your project stack. It auto-detects project types and runs appropriate validation for each.

---

## Phase 0: DETECT Project Type

Detect the project structure and determine validation approach:

```bash
# Check for common project indicators
PROJECT_TYPES=""

# Backend detection
[[ -f "pyproject.toml" ]] && PROJECT_TYPES="$PROJECT_TYPES python"
[[ -f "requirements.txt" ]] && PROJECT_TYPES="$PROJECT_TYPES python"
[[ -f "Cargo.toml" ]] && PROJECT_TYPES="$PROJECT_TYPES rust"
[[ -f "go.mod" ]] && PROJECT_TYPES="$PROJECT_TYPES go"
[[ -d "backend" ]] && HAS_BACKEND=true

# Frontend detection
[[ -f "package.json" ]] && PROJECT_TYPES="$PROJECT_TYPES node"
[[ -d "frontend" ]] && HAS_FRONTEND=true

# Django detection
[[ -f "manage.py" ]] && IS_DJANGO=true
```

Parse `$ARGUMENTS` for scope:
- `all` - Run all validations (default)
- `backend` - Backend only
- `frontend` - Frontend only
- `quick` - Skip E2E and manual tests

---

## Phase 1: Linting (Code Style & Quality)

### Python Backend

```bash
# With Poetry
PYTHONPATH=backend poetry run flake8 backend/apps --max-line-length=100 --count --statistics

# Or with pip
python -m flake8 . --max-line-length=100 --count --statistics
```

### TypeScript/JavaScript Frontend

```bash
cd frontend && npm run lint
# Or
cd frontend && yarn lint
# Or
cd frontend && pnpm lint
```

### Rust

```bash
cargo clippy -- -D warnings
```

### Go

```bash
golangci-lint run
```

**Expected**: No E-class or F-class errors, proper formatting

---

## Phase 2: Type Checking

### Python (MyPy)

```bash
# Strict mode
PYTHONPATH=backend poetry run mypy backend/apps --ignore-missing-imports --strict

# Or relaxed
PYTHONPATH=backend poetry run mypy backend/apps --ignore-missing-imports
```

### TypeScript

```bash
cd frontend && npx tsc --noEmit
```

### Rust

```bash
cargo check
```

**Expected**: Zero type errors, all parameters/returns properly typed

---

## Phase 3: Code Formatting

### Python - Check

```bash
PYTHONPATH=backend poetry run black --check backend/apps
PYTHONPATH=backend poetry run isort --check-only backend/apps
```

### Python - Fix

```bash
PYTHONPATH=backend poetry run black backend/apps
PYTHONPATH=backend poetry run isort backend/apps
```

### TypeScript/JavaScript - Check

```bash
cd frontend && npx prettier --check "src/**/*.{ts,tsx,js,jsx}"
# Or for Next.js
cd frontend && npx prettier --check "app/**/*.{ts,tsx,js,jsx}"
```

### TypeScript/JavaScript - Fix

```bash
cd frontend && npx prettier --write "src/**/*.{ts,tsx,js,jsx}"
```

### Rust

```bash
cargo fmt --check
# Fix with: cargo fmt
```

---

## Phase 4: Unit & Integration Testing

### Python Backend - All Tests with Coverage

```bash
PYTHONPATH=backend poetry run pytest tests/ -v \
  --cov=backend/apps \
  --cov-report=html \
  --cov-report=term-missing:skip-covered
```

### Python - Specific Test Types

```bash
PYTHONPATH=backend poetry run pytest tests/unit/ -v
PYTHONPATH=backend poetry run pytest tests/integration/ -v
```

### TypeScript/JavaScript Frontend

```bash
cd frontend && npm test
# Or with coverage
cd frontend && npm test -- --coverage
```

### Rust

```bash
cargo test
# With coverage (requires cargo-tarpaulin)
cargo tarpaulin --out Html
```

### Go

```bash
go test ./... -v -cover
```

**Coverage Targets**: 80%+ overall, 90%+ critical paths

### View Coverage Report

```bash
# Python
open htmlcov/index.html

# JavaScript
open coverage/lcov-report/index.html
```

### Coverage Persistence

After running tests, save coverage reports to a timestamped directory using the coverage script:

```bash
bash scripts/coverage-report.sh
```

Reports are saved to `.claude/PRPs/coverage/{timestamp}/` and a summary is written to `.claude/PRPs/coverage/latest.json`:

```json
{
  "timestamp": "...",
  "type": "python|node|fullstack",
  "overall_coverage": 85.3,
  "report_path": ".claude/PRPs/coverage/20240115_103000"
}
```

Use `/prp-coverage` for an interactive coverage run with automatic browser opening and target comparison.

---

## Phase 5: Build Verification

### Frontend Build

```bash
cd frontend && npm run build
# Or
cd frontend && yarn build
```

### Backend Build (if applicable)

```bash
# Rust
cargo build --release

# Go
go build ./...

# Python - verify no import errors
PYTHONPATH=backend python -c "import apps"
```

**Expected**: No build errors, clean output

---

## Phase 6: E2E Testing (Skip with `quick` scope)

### 6.1 Environment Connectivity

**Database Connection**:
```bash
# Django
PYTHONPATH=backend python backend/manage.py shell -c "
from django.db import connections
connections['default'].ensure_connection()
print('Database connected')
"
```

**Redis (if applicable)**:
```bash
redis-cli ping
```

### 6.2 API Health Check

```bash
# Start server in background
npm run dev &
# Or
PYTHONPATH=backend python backend/manage.py runserver &

# Test endpoints
curl -s http://localhost:8000/api/health || echo "API not responding"
```

### 6.3 Full-Stack Testing

- [ ] Frontend loads without errors
- [ ] API calls succeed
- [ ] Authentication flows work
- [ ] Key features functional

---

## Phase 7: Security Check

### Python Dependencies

```bash
# Using pip-audit
pip-audit

# Or using safety
safety check
```

### Node Dependencies

```bash
npm audit
# Or
yarn audit
```

### Rust Dependencies

```bash
cargo audit
```

---

## Quick Validation Script

Generate a validation script for the project:

```bash
#!/bin/bash
set -e

echo "=========================================="
echo "Project Comprehensive Validation"
echo "=========================================="

echo -e "\n[PHASE 1] Running Linters..."
# Add detected lint commands

echo -e "\n[PHASE 2] Running Type Checkers..."
# Add detected type check commands

echo -e "\n[PHASE 3] Checking Code Formatting..."
# Add detected format commands

echo -e "\n[PHASE 4] Running Tests with Coverage..."
# Add detected test commands

echo -e "\n[PHASE 5] Building Project..."
# Add detected build commands

echo -e "\n=========================================="
echo "All validations passed!"
echo "=========================================="
```

---

## Validation Report

Generate summary:

```markdown
# Validation Report

**Date**: {date}
**Scope**: {all|backend|frontend|quick}

## Results Summary

| Phase | Status | Details |
|-------|--------|---------|
| Linting | Pass/Fail | {error count} |
| Types | Pass/Fail | {error count} |
| Format | Pass/Fail | {files needing format} |
| Tests | Pass/Fail | {coverage %} |
| Build | Pass/Fail | {details} |
| E2E | Pass/Fail/Skipped | {details} |
| Security | Pass/Fail | {vulnerability count} |

## Issues Found

{List of issues if any}

## Recommendations

{Suggestions for improvement}
```

---

## Success Criteria

All validations pass when:

1. **Linting**: Zero E-class errors, no critical warnings
2. **Type Checking**: Zero type errors
3. **Formatting**: All files formatted consistently
4. **Testing**: 80%+ coverage, all tests pass
5. **Build**: Clean build with no errors
6. **E2E** (if run):
   - Database connectivity verified
   - API endpoints respond correctly
   - Frontend builds and renders
7. **Security**: No high/critical vulnerabilities

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| PYTHONPATH errors | `export PYTHONPATH=backend` |
| Node modules missing | `npm install` or `rm -rf node_modules && npm install` |
| Type errors too strict | Relax with `--ignore-missing-imports --allow-untyped-defs` |
| Test database issues | Ensure test database is configured |
| Build fails | Check for missing dependencies, run clean build |

---

## Output

Report to user:

```
Validation Complete

Scope: {scope}
Duration: {time}

Results:
- Linting: {Pass/Fail}
- Types: {Pass/Fail}
- Format: {Pass/Fail}
- Tests: {Pass/Fail} ({coverage}%)
- Build: {Pass/Fail}
- E2E: {Pass/Fail/Skipped}
- Security: {Pass/Fail}

{If all pass}
All validations passed! Project is in good health.

{If any fail}
Issues found. See details above for fixes.
```
