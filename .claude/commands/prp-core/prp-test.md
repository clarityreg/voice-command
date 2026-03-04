---
description: Generate tests for a file or feature, matching project conventions
argument-hint: <file-or-description>
---

# Test Scaffolding

Generate a test file for the target code, matching the project's existing testing conventions exactly.

## Phase 1: DETECT

Identify the project's test framework and conventions:

1. **Framework** — Check for:
   - Python: `pytest` in pyproject.toml/requirements, `unittest` imports
   - JavaScript/TypeScript: `vitest` / `jest` / `mocha` in package.json
   - Rust: built-in `#[cfg(test)]` / `tests/` directory
   - Go: built-in `_test.go` convention

2. **Existing patterns** — Find 2-3 existing test files and extract:
   - Naming convention (`test_*.py`, `*.test.ts`, `*.spec.ts`, etc.)
   - Directory structure (`tests/unit/`, `__tests__/`, colocated, etc.)
   - Import style and common fixtures/factories/mocks
   - Setup/teardown patterns (conftest.py, beforeEach, test fixtures)
   - Assertion style (`assert`, `expect().toBe()`, etc.)

```bash
# Find existing test files to learn conventions
find . -name "test_*" -o -name "*.test.*" -o -name "*.spec.*" | head -20
```

Read at least 2 existing test files to internalize the patterns.

---

## Phase 2: ANALYZE

Read the target file specified in `$ARGUMENTS`. Extract every testable unit:

1. **Functions/methods** — List each with its signature
2. **Happy paths** — What should work when inputs are valid?
3. **Edge cases** — Empty inputs, boundary values, None/null, max values
4. **Error paths** — What exceptions/errors can be raised? What triggers them?
5. **Side effects** — Database writes, API calls, file I/O that need mocking
6. **Integration points** — Dependencies that tests need to stub/mock

For each testable unit, note:
- Input types and ranges
- Expected outputs
- Error conditions
- Dependencies to mock

---

## Phase 3: SCAFFOLD

Generate the test file following the project's conventions exactly:

### Naming & Location
- Match the project's naming pattern (e.g., `test_auth.py` for `auth.py`)
- Match the directory structure (e.g., `tests/unit/apps/auth/test_views.py` for `backend/apps/auth/views.py`)
- If no clear convention exists, place tests adjacent to the source file

### Structure
- Use the same imports, fixtures, and setup patterns as existing tests
- Group tests logically (by function/class, or by behavior)
- Include:
  - **Happy path tests** — Normal expected behavior
  - **Edge case tests** — Boundary values, empty inputs, large inputs
  - **Error case tests** — Invalid inputs, missing dependencies, permission failures
  - **Integration tests** (if appropriate) — Multi-component interactions

### Comments
Add a brief comment above each test explaining **why** this test exists (not what it does — the test name covers that):

```python
# Ensures expired tokens are rejected even if the signature is valid
def test_authenticate_rejects_expired_token(self):
    ...
```

```typescript
// Verify that concurrent updates don't cause data races on the counter
it('handles concurrent increments correctly', async () => {
    ...
});
```

### Key rules
- **Do NOT impose new patterns** — if the project uses `pytest` fixtures, use those; if it uses `jest` mocks, use those
- **Do NOT add unnecessary dependencies** — only use what's already in the project
- **DO make tests runnable** — correct imports, proper setup, realistic test data

---

## Phase 4: RUN

Execute the generated tests:

```bash
# Python
pytest <test-file> -v

# JavaScript/TypeScript
npx vitest run <test-file>
# or
npx jest <test-file>

# Rust
cargo test <module>::tests

# Go
go test -v -run <TestName> ./<package>/
```

If tests fail due to import errors, missing fixtures, or setup issues:
1. Read the error message
2. Fix the issue in the test file
3. Re-run until tests pass or the failures are genuine (i.e., they found real bugs)

Report any tests that fail due to **actual bugs** in the source code — these are valuable findings.

---

## Phase 5: REPORT

Present results to the user:

```
Test Generation Report
======================

Target: <file-or-function>
Framework: <detected framework>
Test file: <path to generated file>

Tests generated:
  - <count> happy path tests
  - <count> edge case tests
  - <count> error case tests

Results:
  - Passed: <count>
  - Failed: <count> (see details below)
  - Skipped: <count>

Coverage delta: <before>% -> <after>% (+<delta>%)

{If any tests found real bugs}
Potential bugs found:
  - <description of failing test and what it reveals>
```

If no existing test infrastructure exists (no test framework configured, no test directory), inform the user and suggest:
1. Which framework to install
2. How to set up the test directory
3. Offer to create the initial configuration

---

## Output

The primary output is the **test file written to disk**. The report is conversational — do NOT save it as an artifact.
