---
name: detecting-security-antipatterns
description: "Scans code written or edited for common security anti-patterns: hardcoded secrets, SQL injection via string concatenation, eval/exec/innerHTML usage, missing input validation on endpoints, permissive CORS, and DEBUG=True in production configs. Flags issues at write time with severity levels (CRITICAL or WARN) and suggested fixes. Complements pre-commit hooks (bandit, detect-secrets) by catching issues earlier."
---

# Security Anti-Pattern Detection

After code is written or edited, scan for common security anti-patterns and flag them with severity and a suggested fix.

## When to trigger

Activate after any source file is written or edited. Scan the **changed content** (not the entire file) for the patterns below.

Do NOT trigger on:
- Test files (`test_*.py`, `*.test.ts`, `*.spec.ts`, `tests/` directories) — test files often contain mock secrets
- Documentation files (`.md`, `.rst`, `.txt`)
- Lock files (`*.lock`, `package-lock.json`)
- Configuration templates with placeholder values (`*.template.*`, `*.example.*`)

## Patterns to detect

### CRITICAL severity (flag immediately)

| Pattern | Detection | Risk |
|---------|-----------|------|
| **Hardcoded secrets** | Strings matching: `sk-[a-zA-Z0-9]{20,}`, `ghp_[a-zA-Z0-9]{36}`, `AKIA[A-Z0-9]{16}`, `xox[bpsar]-`, `eyJ[a-zA-Z0-9]` (JWT), or variables named `password`, `secret`, `api_key`, `token` assigned string literals (not env lookups) | Credential exposure |
| **SQL string concatenation** | `f"SELECT.*{` or `"SELECT" + ` or `.format(` with SQL keywords, `%s` substitution outside parameterized queries | SQL injection |
| **Shell injection** | `os.system(f"`, `subprocess.call(f"`, `exec(` + user input, backtick interpolation in shell commands | Command injection |

### WARN severity (advisory)

| Pattern | Detection | Risk |
|---------|-----------|------|
| **eval/exec** | `eval(`, `exec(` in Python; `eval(`, `Function(` in JS/TS | Code injection |
| **innerHTML** | `.innerHTML =` with variable content (not static HTML) | XSS |
| **Permissive CORS** | `CORS_ALLOW_ALL_ORIGINS = True`, `Access-Control-Allow-Origin: *`, `cors({ origin: '*' })` or `cors({ origin: true })` | CORS bypass |
| **DEBUG in prod** | `DEBUG = True` in files not named `*dev*`, `*local*`, `*test*` | Information leakage |
| **Disabled SSL verification** | `verify=False`, `rejectUnauthorized: false`, `NODE_TLS_REJECT_UNAUTHORIZED=0` | MITM attacks |
| **Weak crypto** | `md5(`, `sha1(` for password/auth purposes (not checksums), `DES`, `RC4` | Cryptographic weakness |

## How to flag

### CRITICAL issues

Interrupt immediately after the file write with:

> **Security: CRITICAL** — `<pattern-name>` detected in `<file>:<line>`.
> **Risk**: `<one-sentence risk description>`.
> **Fix**: `<specific actionable fix>`.

Example:
> **Security: CRITICAL** — Hardcoded API key detected in `backend/services/payments.py:42`.
> **Risk**: Key will be committed to version control and exposed.
> **Fix**: Move to environment variable: `os.environ["STRIPE_API_KEY"]` and add to `.env`.

### WARN issues

Mention at the end of your response (do not interrupt mid-flow):

> **Security note**: `<pattern-name>` in `<file>:<line>` — `<brief risk>`. Consider: `<fix>`.

## Rules

- **Never block** — flag and move on. The user decides whether to fix.
- **No false positives on test files** — test files intentionally contain mock data.
- **Ignore env lookups** — `os.environ["KEY"]`, `process.env.KEY`, `config("KEY")` are correct patterns, not anti-patterns.
- **Ignore comments** — strings in comments or docstrings are not code.
- **Context matters** — `eval()` in a REPL tool is different from `eval()` in a web handler. Use judgment.
- **Once per issue per file** — do not re-flag the same issue if the user doesn't fix it.
- **Complement, don't duplicate** — if pre-commit hooks (bandit, detect-secrets) will catch the same issue at commit time, still flag at write time but note: "This will also be caught by `<hook>` at commit time."
