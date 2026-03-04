---
name: checking-test-coverage-gaps
description: "Detects when a source file is written or modified that has no corresponding test file. Nudges the user to generate tests with /prp-test. Triggers on edits to backend/*.py, frontend/**/*.ts(x), and src/**/*.ts(x) files — but NOT on test files themselves, config files, migrations, or __init__.py."
---

# Test Coverage Gap Detection

When a source file is written or edited, check whether it has a corresponding test file. If not, prompt the user to generate one.

## When to trigger

Activate after the user writes or edits a **source file** that matches ANY of these patterns:

- `backend/**/*.py` (excluding `__init__.py`, `migrations/`, `conftest.py`, `manage.py`, `settings*.py`, `urls.py`, `admin.py`, `apps.py`)
- `frontend/src/**/*.{ts,tsx}` (excluding `*.test.*`, `*.spec.*`, `*.stories.*`, `*.d.ts`, `index.ts` barrel files)
- `src/**/*.{ts,tsx,js,jsx}` (same exclusions as above)

Do NOT trigger on:
- Test files themselves (`test_*.py`, `*.test.ts`, `*.spec.ts`, `tests/` directories)
- Configuration files (`settings.py`, `config.ts`, `*.config.*`)
- Migration files (`migrations/`, `*.migration.*`)
- Type declaration files (`*.d.ts`)
- Barrel/index files that only re-export
- Files inside `node_modules/`, `.venv/`, `dist/`, `build/`

## How to check for test coverage

1. **Determine the source file path** — e.g., `backend/apps/auth/views.py`

2. **Search for a corresponding test file** using these conventions:

   **Python** (`backend/**/*.py`):
   - Same directory: `test_<filename>.py` (e.g., `test_views.py`)
   - Sibling `tests/` directory: `tests/test_<filename>.py`
   - Top-level `tests/` mirroring the path: `tests/apps/auth/test_views.py`

   **TypeScript/JavaScript** (`frontend/` or `src/`):
   - Same directory: `<filename>.test.ts(x)` or `<filename>.spec.ts(x)`
   - Sibling `__tests__/` directory: `__tests__/<filename>.test.ts(x)`
   - Top-level `tests/` mirroring the path

3. **Use Glob** to search — do not use Bash `find`.

## What to say

### No test file found

> This file (`<relative-path>`) has no tests yet. Run `/prp-test <relative-path>` to generate them?

### Test file exists but source changed significantly

If a test file exists AND the current edit added or changed a public function/method/class/endpoint, mention:

> You modified `<function-name>` in `<file>`. The existing tests in `<test-file>` may need updating — consider running `/prp-test <file>` to check coverage.

Only suggest this for **significant** changes (new functions, changed signatures, new API endpoints). Do NOT nag for minor edits (typo fixes, comment changes, import reordering).

## Rules

- **Never block** — this is advisory only. Present the suggestion and move on.
- **Once per file per session** — do not repeat the nudge if the user ignores it.
- **Do not auto-run** `/prp-test` — only suggest it. The user decides.
- **Be brief** — one or two sentences max. Do not explain why tests are important.
