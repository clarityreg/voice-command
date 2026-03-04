# OWASP Top 10 Security Test Checklist
## Tailored for Bun (Server) + Vue 3 (Client) Stack

### A01:2021 — Broken Access Control
- [ ] Server routes validate authentication before processing
- [ ] API endpoints check authorization (e.g., theme deletion checks authorId)
- [ ] CORS is properly configured (not wildcard `*` in production)
- [ ] WebSocket connections are authenticated
- [ ] Directory traversal prevented in file operations
- [ ] Rate limiting on sensitive endpoints

### A02:2021 — Cryptographic Failures
- [ ] No secrets in source code or config files
- [ ] Environment variables used for sensitive data (API keys, DB creds)
- [ ] HTTPS enforced in production
- [ ] Sensitive data not logged to console
- [ ] Theme share tokens are cryptographically random

### A03:2021 — Injection
- [ ] SQL queries use parameterized statements (SQLite prepared statements)
- [ ] No string concatenation in SQL queries
- [ ] User input sanitized before database operations
- [ ] Theme name validation prevents injection (regex: `^[a-z0-9-_]+$`)
- [ ] JSON parsing wrapped in try/catch
- [ ] No `eval()` or `Function()` with user input

### A04:2021 — Insecure Design
- [ ] Input validation on all API endpoints
- [ ] Request body size limits configured
- [ ] Error messages don't expose internal details
- [ ] Default deny for unknown routes
- [ ] Theme validation enforces all required fields

### A05:2021 — Security Misconfiguration
- [ ] Debug mode disabled in production
- [ ] Default error pages configured
- [ ] Security headers set (CSP, X-Frame-Options, etc.)
- [ ] Unnecessary features/endpoints disabled
- [ ] WAL mode configured for SQLite (prevents corruption)
- [ ] Server port configurable via environment variable

### A06:2021 — Vulnerable and Outdated Components
- [ ] Dependencies audited (`bun audit` / `npm audit`)
- [ ] No known CVEs in dependencies
- [ ] Lock file committed and up to date
- [ ] Trivy scan passing (pre-commit hook)

### A07:2021 — Identification and Authentication Failures
- [ ] WebSocket connections timeout properly
- [ ] HITL response timeout enforced (5s limit)
- [ ] Session IDs are unique and unpredictable
- [ ] No session fixation vulnerabilities

### A08:2021 — Software and Data Integrity Failures
- [ ] Pre-commit hooks enforce code quality
- [ ] Import data validated (theme import)
- [ ] JSON deserialization validates structure
- [ ] No unsafe deserialization

### A09:2021 — Security Logging and Monitoring Failures
- [ ] All API errors logged (console.error)
- [ ] Observability dashboard captures security events
- [ ] Failed authentication/authorization logged
- [ ] Log injection prevented (no user input in log format strings)

### A10:2021 — Server-Side Request Forgery (SSRF)
- [ ] WebSocket URLs validated before connection (HITL responseWebSocketUrl)
- [ ] No user-controlled URLs in server-side requests
- [ ] URL scheme restricted (ws://, wss:// only for WebSocket)
- [ ] Internal network access restricted

---

## Test Execution

| Category | Tests Written | Tests Passing | Coverage |
|----------|:---:|:---:|:---:|
| A01 Access Control | _ / _ | _ / _ | _% |
| A02 Crypto | _ / _ | _ / _ | _% |
| A03 Injection | _ / _ | _ / _ | _% |
| A04 Insecure Design | _ / _ | _ / _ | _% |
| A05 Misconfiguration | _ / _ | _ / _ | _% |
| A06 Components | _ / _ | _ / _ | _% |
| A07 Auth | _ / _ | _ / _ | _% |
| A08 Integrity | _ / _ | _ / _ | _% |
| A09 Logging | _ / _ | _ / _ | _% |
| A10 SSRF | _ / _ | _ / _ | _% |

**Last Audited**: {YYYY-MM-DD}
**Auditor**: {name}
**Overall Status**: {PASS|FAIL|PARTIAL}
