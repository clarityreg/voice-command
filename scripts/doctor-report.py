#!/usr/bin/env python3
"""
doctor-report.py - Generate project health report as HTML or JSON.

Runs 9 groups of health checks (environment, project structure, code health,
git health, Plane integration, PRP components, QA infrastructure, CI/CD, and
observability). Injects results into an HTML template or prints JSON to stdout.

Usage:
    python3 scripts/doctor-report.py          # Generate HTML and open in browser
    python3 scripts/doctor-report.py --json   # Print JSON to stdout (for TUI)
"""

import json
import os
import shutil
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path


# ── Shell helpers ─────────────────────────────────────────────────────────────

def run(cmd: list[str], default: str = "", timeout: int = 15) -> str:
    """Run a shell command and return stdout, or default on failure."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return default


def run_exit_code(cmd: list[str], timeout: int = 15) -> int:
    """Run a shell command and return exit code (1 on failure)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return 1


# ── Settings ──────────────────────────────────────────────────────────────────

def load_settings() -> dict:
    """Load .claude/prp-settings.json."""
    path = Path(".claude/prp-settings.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


# ── Check functions ───────────────────────────────────────────────────────────

def check_environment(settings: dict) -> list[dict]:
    """Check Group 1: required tools and versions."""
    checks = []
    ci = settings.get("ci", {})
    expected_py = ci.get("python_version", "")
    expected_node = ci.get("node_version", "")

    # Python
    py_ver = run(["python3", "--version"]) or run(["python", "--version"])
    if py_ver:
        ver = py_ver.replace("Python ", "")
        if expected_py and not ver.startswith(expected_py):
            checks.append({"name": "Python", "status": "WARN",
                           "detail": f"{ver} (expected: {expected_py})",
                           "fix": f"Install Python {expected_py}"})
        else:
            detail = ver
            if expected_py:
                detail += f" (expected: {expected_py})"
            checks.append({"name": "Python", "status": "PASS", "detail": detail, "fix": ""})
    else:
        checks.append({"name": "Python", "status": "FAIL", "detail": "Not installed",
                        "fix": "Install Python 3"})

    # Node
    node_ver = run(["node", "--version"])
    if node_ver:
        ver = node_ver.lstrip("v")
        if expected_node and not ver.startswith(expected_node):
            checks.append({"name": "Node.js", "status": "WARN",
                           "detail": f"{ver} (expected: {expected_node})",
                           "fix": f"Install Node.js {expected_node}"})
        else:
            detail = ver
            if expected_node:
                detail += f" (expected: {expected_node})"
            checks.append({"name": "Node.js", "status": "PASS", "detail": detail, "fix": ""})
    else:
        checks.append({"name": "Node.js", "status": "FAIL", "detail": "Not installed",
                        "fix": "Install Node.js"})

    # gh CLI
    gh_status = run(["gh", "auth", "status"])
    if gh_status:
        checks.append({"name": "gh CLI", "status": "PASS", "detail": "Authenticated", "fix": ""})
    elif run(["which", "gh"]):
        checks.append({"name": "gh CLI", "status": "WARN", "detail": "Installed but not authenticated",
                        "fix": "Run: gh auth login"})
    else:
        checks.append({"name": "gh CLI", "status": "FAIL", "detail": "Not installed",
                        "fix": "Install GitHub CLI: https://cli.github.com"})

    # pre-commit
    pc_ver = run(["pre-commit", "--version"])
    if pc_ver:
        hooks_installed = Path(".git/hooks/pre-commit").exists()
        if hooks_installed:
            checks.append({"name": "pre-commit", "status": "PASS",
                           "detail": pc_ver + " (hooks installed)", "fix": ""})
        else:
            checks.append({"name": "pre-commit", "status": "WARN",
                           "detail": pc_ver + " (hooks not installed)",
                           "fix": "Run: pre-commit install"})
    else:
        pip_cmd = "uv pip install" if shutil.which("uv") else "pip install"
        checks.append({"name": "pre-commit", "status": "SKIP", "detail": "Not installed (optional)",
                        "fix": f"{pip_cmd} pre-commit"})

    # ruff
    ruff_ver = run(["ruff", "--version"])
    if ruff_ver:
        checks.append({"name": "ruff", "status": "PASS", "detail": ruff_ver, "fix": ""})
    else:
        pip_cmd = "uv pip install" if shutil.which("uv") else "pip install"
        checks.append({"name": "ruff", "status": "SKIP", "detail": "Not installed (optional)",
                        "fix": f"{pip_cmd} ruff"})

    # trivy
    trivy_ver = run(["trivy", "--version"])
    if trivy_ver:
        ver_line = trivy_ver.splitlines()[0] if trivy_ver else ""
        checks.append({"name": "trivy", "status": "PASS", "detail": ver_line, "fix": ""})
    else:
        checks.append({"name": "trivy", "status": "SKIP", "detail": "Not installed (optional)",
                        "fix": "brew install trivy"})

    return checks


def check_project_structure(settings: dict) -> list[dict]:
    """Check Group 2: essential files and directories."""
    checks = []
    project = settings.get("project", {})

    # .env
    if Path(".env.example").exists():
        if Path(".env").exists():
            # Compare keys
            example_keys = _env_keys(".env.example")
            env_keys = _env_keys(".env")
            missing = example_keys - env_keys
            if missing:
                checks.append({"name": ".env", "status": "WARN",
                               "detail": f"Missing keys: {', '.join(sorted(missing))}",
                               "fix": "Add missing keys to .env"})
            else:
                checks.append({"name": ".env", "status": "PASS",
                               "detail": "All keys from .env.example present", "fix": ""})
        else:
            checks.append({"name": ".env", "status": "FAIL",
                           "detail": ".env.example exists but .env does not",
                           "fix": "cp .env.example .env and fill in values"})
    else:
        checks.append({"name": ".env", "status": "SKIP",
                       "detail": "No .env.example found", "fix": ""})

    # prp-settings.json
    if Path(".claude/prp-settings.json").exists():
        name = project.get("name", "")
        if name:
            checks.append({"name": "prp-settings.json", "status": "PASS",
                           "detail": f'Configured (project: "{name}")', "fix": ""})
        else:
            checks.append({"name": "prp-settings.json", "status": "WARN",
                           "detail": "Exists but project.name is empty",
                           "fix": "Set project.name in .claude/prp-settings.json"})
    else:
        checks.append({"name": "prp-settings.json", "status": "FAIL",
                       "detail": "Not found", "fix": "Run setup-prp.sh or create manually"})

    # Backend dir
    backend = project.get("backend_dir", "backend")
    if backend:
        if Path(backend).is_dir():
            checks.append({"name": f"Backend ({backend}/)", "status": "PASS",
                           "detail": "Directory exists", "fix": ""})
        else:
            checks.append({"name": f"Backend ({backend}/)", "status": "WARN",
                           "detail": "Configured but directory missing",
                           "fix": f"Create {backend}/ or update project.backend_dir"})
    else:
        checks.append({"name": "Backend", "status": "SKIP",
                       "detail": "Not configured", "fix": ""})

    # Frontend dir
    frontend = project.get("frontend_dir", "frontend")
    if frontend:
        if Path(frontend).is_dir():
            checks.append({"name": f"Frontend ({frontend}/)", "status": "PASS",
                           "detail": "Directory exists", "fix": ""})
        else:
            checks.append({"name": f"Frontend ({frontend}/)", "status": "WARN",
                           "detail": "Configured but directory missing",
                           "fix": f"Create {frontend}/ or update project.frontend_dir"})
    else:
        checks.append({"name": "Frontend", "status": "SKIP",
                       "detail": "Not configured", "fix": ""})

    # Test directory
    test_dirs = ["tests", "test", "__tests__"]
    found_tests = any(Path(d).is_dir() for d in test_dirs)
    if not found_tests:
        # Check for *.test.* files
        for ext in ("*.test.py", "*.test.ts", "*.test.tsx", "*.test.js"):
            result = run(["find", ".", "-name", ext, "-not", "-path", "*/node_modules/*", "-maxdepth", "4"])
            if result:
                found_tests = True
                break
    if found_tests:
        checks.append({"name": "Test directory", "status": "PASS",
                       "detail": "Test files found", "fix": ""})
    else:
        checks.append({"name": "Test directory", "status": "WARN",
                       "detail": "No test directory or test files found",
                       "fix": "Create tests/ directory"})

    # README
    if Path("README.md").exists():
        lines = len(Path("README.md").read_text().splitlines())
        checks.append({"name": "README.md", "status": "PASS",
                       "detail": f"Exists ({lines} lines)", "fix": ""})
    else:
        checks.append({"name": "README.md", "status": "WARN",
                       "detail": "Not found", "fix": "Create a README.md"})

    return checks


def check_code_health(settings: dict) -> list[dict]:
    """Check Group 3: code quality signals."""
    checks = []

    # Oversized Python files
    oversized = []
    for py_file in Path(".").rglob("*.py"):
        parts = py_file.parts
        if any(p in parts for p in ("node_modules", ".venv", "venv", "migrations", "__pycache__")):
            continue
        try:
            lines = len(py_file.read_text().splitlines())
            if lines > 500:
                oversized.append((str(py_file), lines))
        except OSError:
            pass
    if oversized:
        detail = f"{len(oversized)} file(s) over 500 lines"
        fix_parts = [f"{f} ({n} lines)" for f, n in sorted(oversized)]
        checks.append({"name": "Python file size", "status": "WARN",
                       "detail": detail, "fix": "; ".join(fix_parts)})
    else:
        checks.append({"name": "Python file size", "status": "PASS",
                       "detail": "No files over 500 lines", "fix": ""})

    # TODO/FIXME count
    todo_output = run([
        "grep", "-rn", r"TODO\|FIXME\|HACK\|XXX",
        "--include=*.py", "--include=*.ts", "--include=*.tsx",
        "--include=*.js", "--include=*.jsx", ".",
    ])
    todo_lines = [l for l in todo_output.splitlines()
                  if "node_modules" not in l and ".venv" not in l] if todo_output else []
    checks.append({"name": "TODO/FIXME markers", "status": "INFO",
                   "detail": f"{len(todo_lines)} markers found", "fix": ""})

    # Coverage
    coverage_path = Path(".claude/PRPs/coverage/latest.json")
    if coverage_path.exists():
        try:
            cov_data = json.loads(coverage_path.read_text())
            overall = cov_data.get("overall_coverage", 0)
            target = settings.get("coverage", {}).get("targets", {}).get("overall", 80)
            if overall >= target:
                checks.append({"name": "Test coverage", "status": "PASS",
                               "detail": f"{overall}% (target: {target}%)", "fix": ""})
            else:
                checks.append({"name": "Test coverage", "status": "WARN",
                               "detail": f"{overall}% (target: {target}%)",
                               "fix": "Run /prp-coverage and add missing tests"})
        except (json.JSONDecodeError, OSError):
            checks.append({"name": "Test coverage", "status": "SKIP",
                           "detail": "Coverage file unreadable", "fix": ""})
    else:
        checks.append({"name": "Test coverage", "status": "SKIP",
                       "detail": "No coverage report found",
                       "fix": "Run /prp-coverage to generate"})

    # Merge conflict markers
    conflict_files = run(["git", "grep", "-l", r"<<<<<<< \|======= \|>>>>>>> ", "--", ":!*.md"])
    if conflict_files:
        files = conflict_files.splitlines()
        checks.append({"name": "Merge conflicts", "status": "FAIL",
                       "detail": f"{len(files)} file(s) with conflict markers",
                       "fix": "; ".join(files)})
    else:
        checks.append({"name": "Merge conflicts", "status": "PASS",
                       "detail": "No conflict markers found", "fix": ""})

    return checks


def check_git_health() -> list[dict]:
    """Check Group 4: repository state."""
    checks = []

    # Current branch
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if branch in ("main", "master"):
        checks.append({"name": "Branch", "status": "WARN",
                       "detail": f"On protected branch: {branch}",
                       "fix": "Switch to a feature branch"})
    elif branch:
        checks.append({"name": "Branch", "status": "PASS",
                       "detail": f"On branch: {branch}", "fix": ""})
    else:
        checks.append({"name": "Branch", "status": "FAIL",
                       "detail": "Not in a git repository", "fix": "Run: git init"})

    # Uncommitted changes
    status_output = run(["git", "status", "--porcelain"])
    if status_output:
        count = len(status_output.splitlines())
        checks.append({"name": "Working tree", "status": "WARN",
                       "detail": f"{count} uncommitted change(s)",
                       "fix": "Commit or stash your changes"})
    else:
        checks.append({"name": "Working tree", "status": "PASS",
                       "detail": "Clean", "fix": ""})

    # Stale branches
    main = "main" if run_exit_code(["git", "rev-parse", "--verify", "main"]) == 0 else "master"
    merged = run(["git", "branch", "--merged", main])
    if merged:
        stale = [b.strip() for b in merged.splitlines()
                 if b.strip() and b.strip() not in ("main", "master") and not b.strip().startswith("*")]
        if stale:
            checks.append({"name": "Stale branches", "status": "WARN",
                           "detail": f"{len(stale)} merged but not deleted",
                           "fix": "git branch -d " + " ".join(stale)})
        else:
            checks.append({"name": "Stale branches", "status": "PASS",
                           "detail": "No stale branches", "fix": ""})
    else:
        checks.append({"name": "Stale branches", "status": "PASS",
                       "detail": "No stale branches", "fix": ""})

    # Remote
    remote_url = run(["git", "remote", "get-url", "origin"])
    if remote_url:
        reachable = run_exit_code(["git", "ls-remote", "--exit-code", "origin", "HEAD"]) == 0
        if reachable:
            checks.append({"name": "Remote", "status": "PASS",
                           "detail": f"origin -> {remote_url} (reachable)", "fix": ""})
        else:
            checks.append({"name": "Remote", "status": "WARN",
                           "detail": f"origin -> {remote_url} (unreachable)",
                           "fix": "Check network connection or remote URL"})
    else:
        checks.append({"name": "Remote", "status": "FAIL",
                       "detail": "No remote configured",
                       "fix": "git remote add origin <url>"})

    return checks


def check_plane(settings: dict) -> list[dict]:
    """Check Group 5: Plane/Archon integration."""
    plane = settings.get("plane", {})
    slug = plane.get("workspace_slug", "")
    project_id = plane.get("project_id", "")

    if not slug or not project_id:
        return [{"name": "Plane", "status": "SKIP",
                 "detail": "Not configured (workspace_slug or project_id empty)", "fix": ""}]

    checks = []
    api_key = os.environ.get("PLANE_API_KEY", "")
    if not api_key:
        # Fall back to .claude/prp-secrets.env
        secrets_path = Path(".claude/prp-secrets.env")
        if secrets_path.exists():
            for line in secrets_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("PLANE_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip("\"'")
                    break
    api_url = plane.get("api_url", "https://api.plane.so/api/v1")

    if not api_key:
        checks.append({"name": "Plane API key", "status": "FAIL",
                       "detail": "PLANE_API_KEY not set",
                       "fix": "Add PLANE_API_KEY to .claude/prp-secrets.env or export in shell"})
        return checks

    # API reachable
    url = f"{api_url}/workspaces/{slug}/projects/{project_id}/"
    code = run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                "-H", f"X-API-Key: {api_key}", url], timeout=5)
    if code == "200":
        checks.append({"name": "Plane API", "status": "PASS",
                       "detail": "Reachable (200)", "fix": ""})
        checks.append({"name": "Project ID", "status": "PASS",
                       "detail": f"Valid ({project_id[:8]}...)", "fix": ""})
    else:
        checks.append({"name": "Plane API", "status": "FAIL",
                       "detail": f"Status {code}",
                       "fix": "Check workspace_slug, project_id, and API key"})

    return checks


def check_prp_components() -> list[dict]:
    """Check Group 6: PRP component installation."""
    checks = []
    components = [
        ("Core commands", ".claude/commands/prp-core"),
        ("Hook scripts", ".claude/hooks"),
        ("Git guard scripts", ".claude/scripts"),
        ("Skills", ".claude/skills"),
        ("Agents", ".claude/agents"),
        ("CI templates", ".claude/templates/ci"),
        ("Pre-commit config", ".pre-commit-config.yaml"),
        ("Settings wiring", ".claude/settings.json"),
        ("Observability dashboard", "apps/server"),
        ("Ralph loop", "ralph"),
    ]

    for label, path in components:
        p = Path(path)
        if p.exists():
            if p.is_dir():
                count = sum(1 for _ in p.rglob("*") if _.is_file())
                checks.append({"name": label, "status": "PASS",
                               "detail": f"{path}/ ({count} files)", "fix": ""})
            else:
                checks.append({"name": label, "status": "PASS",
                               "detail": f"{path} exists", "fix": ""})
        else:
            checks.append({"name": label, "status": "WARN",
                           "detail": f"{path} not found",
                           "fix": f"Run install-prp.sh to install"})

    return checks


def check_qa_infrastructure(settings: dict) -> list[dict]:
    """Check Group 7: QA infrastructure."""
    checks = []
    qa = settings.get("qa", {})

    # QA directory
    if Path(".claude/PRPs/qa").is_dir():
        checks.append({"name": "QA directory", "status": "PASS",
                       "detail": ".claude/PRPs/qa/ exists", "fix": ""})
    else:
        checks.append({"name": "QA directory", "status": "WARN",
                       "detail": "Not found",
                       "fix": "Run /prp-qa-init to scaffold QA infrastructure"})

    # test-results.csv
    csv_path = qa.get("tracking_csv", ".claude/PRPs/qa/test-results.csv")
    if Path(csv_path).exists():
        checks.append({"name": "Test results CSV", "status": "PASS",
                       "detail": f"{csv_path} exists", "fix": ""})
    else:
        checks.append({"name": "Test results CSV", "status": "WARN",
                       "detail": "Not found",
                       "fix": "Run /prp-qa-init or /prp-coverage to create"})

    # Quality gates in settings
    gates = qa.get("quality_gates", {})
    if gates:
        checks.append({"name": "Quality gates", "status": "PASS",
                       "detail": f"Configured (min_coverage: {gates.get('min_coverage', '?')}%)",
                       "fix": ""})
    else:
        checks.append({"name": "Quality gates", "status": "WARN",
                       "detail": "Not configured in settings",
                       "fix": "Add qa.quality_gates to prp-settings.json"})

    # QA gate check script
    if Path("scripts/qa-gate-check.sh").exists():
        checks.append({"name": "QA gate script", "status": "PASS",
                       "detail": "scripts/qa-gate-check.sh exists", "fix": ""})
    else:
        checks.append({"name": "QA gate script", "status": "SKIP",
                       "detail": "Not found (optional)", "fix": ""})

    return checks


def check_ci_cd() -> list[dict]:
    """Check Group 8: CI/CD configuration."""
    checks = []

    # GitHub Actions
    ci_yml = Path(".github/workflows/ci.yml")
    if ci_yml.exists():
        checks.append({"name": "CI workflow", "status": "PASS",
                       "detail": ".github/workflows/ci.yml exists", "fix": ""})
    else:
        checks.append({"name": "CI workflow", "status": "WARN",
                       "detail": "Not found",
                       "fix": "Run /prp-ci-init to generate from templates"})

    deploy_yml = Path(".github/workflows/deploy.yml")
    if deploy_yml.exists():
        checks.append({"name": "Deploy workflow", "status": "PASS",
                       "detail": ".github/workflows/deploy.yml exists", "fix": ""})
    else:
        checks.append({"name": "Deploy workflow", "status": "SKIP",
                       "detail": "Not found (optional)", "fix": ""})

    # CI templates
    template_dir = Path(".claude/templates/ci")
    if template_dir.is_dir():
        templates = list(template_dir.glob("*.template"))
        checks.append({"name": "CI templates", "status": "PASS",
                       "detail": f"{len(templates)} template(s) in .claude/templates/ci/",
                       "fix": ""})
    else:
        checks.append({"name": "CI templates", "status": "WARN",
                       "detail": "Template directory not found",
                       "fix": "Install PRP CI templates"})

    return checks


def check_observability() -> list[dict]:
    """Check Group 9: observability dashboard."""
    checks = []

    # Server health
    health = run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                  "--connect-timeout", "2", "http://localhost:4000/health"], timeout=3)
    if health == "200":
        checks.append({"name": "Observability server", "status": "PASS",
                       "detail": "Running on localhost:4000", "fix": ""})
    else:
        checks.append({"name": "Observability server", "status": "WARN",
                       "detail": "Not running",
                       "fix": "Run: ./scripts/start-observability.sh"})

    # Check if apps directory exists
    if Path("apps/server").is_dir() and Path("apps/client").is_dir():
        checks.append({"name": "Dashboard files", "status": "PASS",
                       "detail": "apps/server/ + apps/client/ present", "fix": ""})
    else:
        checks.append({"name": "Dashboard files", "status": "WARN",
                       "detail": "Dashboard source not found",
                       "fix": "Install observability component via install-prp.sh"})

    return checks


# ── Helpers ───────────────────────────────────────────────────────────────────

def _env_keys(path: str) -> set[str]:
    """Extract KEY names from a .env file (ignoring comments and blanks)."""
    keys = set()
    try:
        for line in Path(path).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                keys.add(line.split("=", 1)[0].strip())
    except OSError:
        pass
    return keys


def compute_score(groups: list[dict]) -> dict:
    """Compute overall score from all check groups."""
    total = 0
    passed = 0
    warns = 0
    fails = 0
    skips = 0
    infos = 0

    for group in groups:
        for check in group["checks"]:
            s = check["status"]
            if s == "SKIP" or s == "INFO":
                if s == "SKIP":
                    skips += 1
                else:
                    infos += 1
                continue
            total += 1
            if s == "PASS":
                passed += 1
            elif s == "WARN":
                warns += 1
            elif s == "FAIL":
                fails += 1

    pct = round(passed / total * 100) if total > 0 else 0
    return {
        "total": total,
        "passed": passed,
        "warns": warns,
        "fails": fails,
        "skips": skips,
        "infos": infos,
        "percentage": pct,
    }


def build_report(settings: dict) -> dict:
    """Run all check groups and assemble the report."""
    groups = [
        {"name": "Environment", "checks": check_environment(settings)},
        {"name": "Project Structure", "checks": check_project_structure(settings)},
        {"name": "Code Health", "checks": check_code_health(settings)},
        {"name": "Git Health", "checks": check_git_health()},
        {"name": "Plane Integration", "checks": check_plane(settings)},
        {"name": "PRP Components", "checks": check_prp_components()},
        {"name": "QA Infrastructure", "checks": check_qa_infrastructure(settings)},
        {"name": "CI/CD", "checks": check_ci_cd()},
        {"name": "Observability", "checks": check_observability()},
    ]

    score = compute_score(groups)
    project_name = settings.get("project", {}).get("name", "") or Path.cwd().name

    return {
        "project_name": project_name,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "groups": groups,
        "score": score,
    }


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if not Path(".git").exists():
        print("Error: Not in a git repository root.", file=sys.stderr)
        sys.exit(1)

    settings = load_settings()
    report = build_report(settings)

    # JSON mode for TUI consumption
    if "--json" in sys.argv:
        print(json.dumps(report, indent=2))
        return

    # HTML mode — inject into template
    print("Running health checks...")
    data_json = json.dumps(report, indent=2)

    template_path = Path(__file__).parent / "doctor-report-template.html"
    if not template_path.exists():
        print(f"Error: Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    template = template_path.read_text(encoding="utf-8")
    html = template.replace("{{DOCTOR_DATA}}", data_json)

    output_dir = Path(".claude/PRPs/doctor")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "doctor-report.html"
    output_file.write_text(html, encoding="utf-8")

    score = report["score"]
    print(f"\nHealth report: {score['passed']}/{score['total']} pass, "
          f"{score['warns']} warn, {score['fails']} fail")
    print(f"Saved: {output_file}")

    abs_path = output_file.resolve()
    url = f"file://{abs_path}"
    print(f"Opening: {url}")
    webbrowser.open(url)


if __name__ == "__main__":
    main()
