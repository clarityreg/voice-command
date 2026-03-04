---
description: Run tests and generate coverage reports
argument-hint: [python|node|all]
---

# Coverage Report

Run tests with coverage instrumentation, save timestamped reports to `.claude/PRPs/coverage/`, and open the HTML report in your browser.

## Usage

```bash
/prp-coverage          # Auto-detect project type and run all coverage
/prp-coverage python   # Python only
/prp-coverage node     # Node/Vitest only
```

---

## Phase 1: RUN COVERAGE

Execute the coverage script:

```bash
bash scripts/coverage-report.sh
```

The script auto-detects project type from:
- `pyproject.toml` / `requirements.txt` → Python (pytest + coverage)
- `package.json` → Node (vitest --coverage)
- Both present → Fullstack (runs both)

### Python coverage commands used internally:

```bash
PYTHONPATH=backend pytest tests/ \
  --cov=backend \
  --cov-report=html:htmlcov \
  --cov-report=json:coverage.json \
  --cov-report=term-missing:skip-covered
```

### Node coverage commands used internally:

```bash
npx vitest run --coverage
```

---

## Phase 2: READ LATEST SUMMARY

After the script completes, read the summary:

```bash
cat .claude/PRPs/coverage/latest.json
```

The JSON contains:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "type": "python|node|fullstack",
  "overall_coverage": 85.3,
  "python_coverage": 85.3,
  "node_coverage": null,
  "report_path": ".claude/PRPs/coverage/20240115_103000",
  "html_report": ".claude/PRPs/coverage/20240115_103000/python-html/index.html"
}
```

---

## Phase 3: CHECK AGAINST TARGETS

Read coverage targets from `.claude/prp-settings.json`:

```json
{
  "coverage": {
    "targets": { "overall": 80, "critical": 90 }
  }
}
```

Compare `overall_coverage` against `targets.overall`:

- **Pass** (≥ target): Report coverage and proceed
- **Fail** (< target): Report gap and suggest files to improve

---

## Phase 4: REPORT

Output summary to user:

```
Coverage Report
===============
Type:     python
Overall:  85.3%  ✓ (target: 80%)
Report:   .claude/PRPs/coverage/20240115_103000/

HTML opened in browser.

Next: /prp-validate to run full project validation
```

If below target:
```
Coverage Report
===============
Overall:  72.1%  ✗ (target: 80%)
Gap:      7.9% — add tests to reach target

Lowest covered modules:
  - backend/apps/auth/views.py (52%)
  - backend/apps/api/serializers.py (61%)

Run: pytest tests/ --cov=backend --cov-report=term-missing
```

---

## Integration with PRP Workflow

```bash
# After implementation
/prp-implement .claude/PRPs/plans/my-feature.plan.md

# Check coverage
/prp-coverage

# Then validate everything
/prp-validate

# Then review and PR
/prp-coderabbit branch:main
/prp-pr
```

---

## Historical Reports

Coverage reports are saved with timestamps and never overwritten:

```
.claude/PRPs/coverage/
├── latest.json                  ← Always points to most recent run
├── 20240115_103000/
│   └── python-html/index.html
├── 20240114_090000/
│   └── python-html/index.html
└── ...
```

To view a past report:
```bash
open .claude/PRPs/coverage/20240114_090000/python-html/index.html
```
