"""Error investigation via Claude CLI subprocess.

Analyzes triage item context and returns structured diagnosis.
Gracefully falls back when Claude CLI is not available.
"""

import asyncio
import json
import shutil

_CLAUDE_PATH: str | None = shutil.which("claude")


async def investigate(title: str, description: str, severity: str, source: str, metadata: dict) -> dict:
    """Investigate an error using Claude CLI subprocess.

    Returns a dict with keys: root_cause, affected_files, suggested_fix, raw_response.
    Falls back to a manual template if Claude CLI is unavailable.
    """
    if not _CLAUDE_PATH:
        return _fallback_result(title, description, severity, source)

    prompt = _build_prompt(title, description, severity, source, metadata)

    try:
        proc = await asyncio.create_subprocess_exec(
            _CLAUDE_PATH, "-p", prompt, "--output-format", "json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

        if proc.returncode != 0:
            return _fallback_result(title, description, severity, source)

        raw = stdout.decode().strip()
        # Try to parse Claude's JSON response
        try:
            parsed = json.loads(raw)
            # Claude --output-format json wraps in {"result": "..."}
            text = parsed.get("result", raw) if isinstance(parsed, dict) else raw
        except json.JSONDecodeError:
            text = raw

        return _parse_investigation(text, title)

    except (asyncio.TimeoutError, OSError):
        return _fallback_result(title, description, severity, source)


def _build_prompt(title: str, description: str, severity: str, source: str, metadata: dict) -> str:
    meta_summary = ""
    if metadata:
        meta_summary = f"\nAdditional context: {json.dumps(metadata, default=str)[:500]}"

    return f"""Analyze this {source} error and provide a structured diagnosis.

Error: {title}
Description: {description}
Severity: {severity}{meta_summary}

Respond in this exact format:
ROOT CAUSE: <one paragraph explaining the likely root cause>
AFFECTED FILES: <comma-separated list of likely affected files or "Unknown">
SUGGESTED FIX: <concise actionable fix recommendation>"""


def _parse_investigation(text: str, title: str) -> dict:
    """Parse Claude's response into structured fields."""
    result = {
        "root_cause": "",
        "affected_files": [],
        "suggested_fix": "",
        "raw_response": text[:2000],
    }

    lines = text.strip().split("\n")
    current_field = None

    for line in lines:
        upper = line.strip().upper()
        if upper.startswith("ROOT CAUSE:"):
            current_field = "root_cause"
            result["root_cause"] = line.split(":", 1)[1].strip()
        elif upper.startswith("AFFECTED FILES:"):
            current_field = "affected_files"
            files_str = line.split(":", 1)[1].strip()
            if files_str.lower() != "unknown":
                result["affected_files"] = [f.strip() for f in files_str.split(",") if f.strip()]
        elif upper.startswith("SUGGESTED FIX:"):
            current_field = "suggested_fix"
            result["suggested_fix"] = line.split(":", 1)[1].strip()
        elif current_field and current_field != "affected_files":
            result[current_field] += " " + line.strip()  # type: ignore[operator]

    # Clean up
    for key in ("root_cause", "suggested_fix"):
        result[key] = result[key].strip()  # type: ignore[union-attr]

    return result


def _fallback_result(title: str, description: str, severity: str, source: str) -> dict:
    """Return a template when Claude CLI is unavailable."""
    return {
        "root_cause": f"Automated investigation unavailable. This {severity} {source} error requires manual review.",
        "affected_files": [],
        "suggested_fix": f"Review the error '{title}' manually. Check logs and stack traces for more context.",
        "raw_response": "Claude CLI not available — manual investigation needed.",
    }
