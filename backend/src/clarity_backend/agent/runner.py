"""Agent runner — creates plans and executes fixes via Claude CLI subprocess.

Uses --output-format stream-json for incremental progress streaming over WebSocket.
Gracefully degrades when Claude CLI is not installed.
"""

import asyncio
import json
import shutil
from typing import Any

from clarity_backend.models import utcnow

_CLAUDE_PATH: str | None = shutil.which("claude")
CLAUDE_CLI_AVAILABLE: bool = _CLAUDE_PATH is not None


async def _broadcast(event: str, data: dict) -> None:
    """Send a raw JSON message to all active WebSocket connections."""
    from clarity_backend.notifications.ws import ws_manager

    msg = json.dumps({"event": event, "data": data})
    dead = set()
    for conn in list(ws_manager.active_connections):
        try:
            await conn.send_text(msg)
        except Exception:
            dead.add(conn)
    ws_manager.active_connections -= dead


async def _drain(stream: asyncio.StreamReader) -> bytes:
    """Read all bytes from an asyncio stream."""
    chunks: list[bytes] = []
    while True:
        chunk = await stream.read(4096)
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


def _extract_posthog_context(item_dict: dict) -> str:
    """Return a formatted PostHog context block, or empty string if unavailable.

    Parses the ``metadata_json`` field (a JSON string) that the PostHog poller
    stores on every TriageItem.  Only fields that are non-empty are included so
    the prompt stays clean when data is partial.
    """
    raw = item_dict.get("metadata_json", "{}")
    if not raw:
        return ""
    try:
        meta: dict = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return ""

    # PostHog stores the original event at top level; properties are nested.
    props: dict = meta.get("properties", {})

    lines: list[str] = []

    current_url = props.get("$current_url", "")
    if current_url:
        lines.append(f"  Error URL: {current_url}")

    distinct_id = meta.get("distinct_id", "")
    if distinct_id:
        lines.append(f"  Affected user: {distinct_id}")

    exc_type = props.get("$exception_type", "")
    if exc_type:
        lines.append(f"  Exception type: {exc_type}")

    browser = props.get("$browser", "")
    os_name = props.get("$os", "")
    if browser or os_name:
        env_parts = [p for p in (browser, os_name) if p]
        lines.append(f"  Client environment: {', '.join(env_parts)}")

    if not lines:
        return ""

    return "\nPostHog session context:\n" + "\n".join(lines)


def _build_planning_prompt(item_dict: dict) -> str:
    occurrence_count = item_dict.get("occurrence_count", 1)
    first_seen = item_dict.get("first_seen", "unknown")
    last_seen = item_dict.get("last_seen", "unknown")
    posthog_ctx = _extract_posthog_context(item_dict)

    return f"""You are a senior software engineer performing a root cause analysis.

Triage item:
  Title: {item_dict.get("title", "Unknown")}
  Source: {item_dict.get("source", "Unknown")}
  Severity: {item_dict.get("severity", "unknown")}
  Description: {item_dict.get("description", "")}

Error context:
  Occurrences: {occurrence_count} (first seen: {first_seen}, last seen: {last_seen})
{posthog_ctx}
Investigate the codebase and produce a structured fix plan covering:
1. ROOT CAUSE — explain why this error occurs
2. FILES TO MODIFY — list each file path and what change is needed
3. IMPLEMENTATION STEPS — numbered list of concrete code changes
4. TESTING APPROACH — how to verify the fix works
5. RISK ASSESSMENT — potential side effects or regressions

Be concise and specific. Output plain text only."""


def _build_execute_prompt(plan_text: str) -> str:
    return f"""You are a senior software engineer implementing an approved fix plan.

Follow the plan below precisely. Make only the changes described — nothing more.
When done, run `git commit -am "<descriptive message>"` with a clear commit message.
Do NOT push to remote.

APPROVED PLAN:
{plan_text}"""


async def create_plan(job_id: str, session_factory: Any, item_dict: dict) -> None:
    """Run Claude in read-only mode to draft a fix plan.

    Streams progress events over WebSocket. Updates the AgentJob record on
    completion or failure.
    """
    from clarity_backend.agent.models import AgentJob

    async with session_factory() as session:
        job = await session.get(AgentJob, job_id)
        if not job or job.status == "cancelled":
            return
        job.status = "planning"
        job.updated_at = utcnow()
        session.add(job)
        await session.commit()

    await _broadcast(
        "agent_progress",
        {"job_id": job_id, "phase": "planning", "message": "Starting plan creation…"},
    )

    if not _CLAUDE_PATH:
        async with session_factory() as session:
            job = await session.get(AgentJob, job_id)
            if job:
                job.status = "failed"
                job.error_message = "Claude CLI not available on this system"
                job.updated_at = utcnow()
                session.add(job)
                await session.commit()
        await _broadcast(
            "agent_progress",
            {"job_id": job_id, "phase": "failed", "message": "Claude CLI not available"},
        )
        return

    prompt = _build_planning_prompt(item_dict)
    events: list[dict] = []
    plan_text = ""

    try:
        proc = await asyncio.create_subprocess_exec(
            _CLAUDE_PATH,
            "-p",
            prompt,
            "--output-format",
            "stream-json",
            "--allowedTools",
            "Read,Glob,Grep",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert proc.stdout is not None
        assert proc.stderr is not None

        stderr_task = asyncio.create_task(_drain(proc.stderr))

        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            line_str = line.decode().strip()
            if not line_str:
                continue
            try:
                event_data = json.loads(line_str)
                events.append(event_data)
                if isinstance(event_data, dict):
                    if event_data.get("type") == "result":
                        plan_text = event_data.get("result", "")
                    elif event_data.get("type") == "text":
                        plan_text += event_data.get("text", "")
                await _broadcast(
                    "agent_progress", {"job_id": job_id, "phase": "planning", "event": event_data}
                )
            except json.JSONDecodeError:
                pass

        await proc.wait()
        stderr_bytes = await stderr_task

        if proc.returncode != 0:
            err_msg = stderr_bytes.decode()[:500]
            async with session_factory() as session:
                job = await session.get(AgentJob, job_id)
                if job:
                    job.status = "failed"
                    job.error_message = f"Claude exited {proc.returncode}: {err_msg}"
                    job.events_json = json.dumps(events)
                    job.updated_at = utcnow()
                    session.add(job)
                    await session.commit()
            await _broadcast(
                "agent_progress", {"job_id": job_id, "phase": "failed", "message": err_msg}
            )
            return

        async with session_factory() as session:
            job = await session.get(AgentJob, job_id)
            if job and job.status != "cancelled":
                job.status = "plan_ready"
                job.plan_text = plan_text.strip()
                job.events_json = json.dumps(events)
                job.updated_at = utcnow()
                session.add(job)
                await session.commit()

        await _broadcast(
            "agent_progress",
            {"job_id": job_id, "phase": "plan_ready", "message": "Plan ready for review"},
        )

    except Exception as exc:
        async with session_factory() as session:
            job = await session.get(AgentJob, job_id)
            if job:
                job.status = "failed"
                job.error_message = str(exc)[:500]
                job.updated_at = utcnow()
                session.add(job)
                await session.commit()
        await _broadcast(
            "agent_progress", {"job_id": job_id, "phase": "failed", "message": str(exc)[:200]}
        )


async def execute_plan(job_id: str, session_factory: Any) -> None:
    """Execute an approved plan inside a git worktree.

    Creates a branch `fix/agent-{id[:8]}` at `/tmp/clarity-agent-{id[:8]}`,
    runs Claude with edit tools, stores the branch name on success.
    Cleans up the worktree in all cases.
    """
    from clarity_backend.agent.models import AgentJob

    short_id = job_id[:8]
    worktree_path = f"/tmp/clarity-agent-{short_id}"
    branch_name = f"fix/agent-{short_id}"

    async with session_factory() as session:
        job = await session.get(AgentJob, job_id)
        if not job or job.status == "cancelled":
            return
        if not job.plan_text:
            job.status = "failed"
            job.error_message = "No plan text found — approve a plan first"
            job.updated_at = utcnow()
            session.add(job)
            await session.commit()
            await _broadcast(
                "agent_progress",
                {"job_id": job_id, "phase": "failed", "message": job.error_message},
            )
            return
        plan_text = job.plan_text
        job.status = "running"
        job.updated_at = utcnow()
        session.add(job)
        await session.commit()

    await _broadcast(
        "agent_progress", {"job_id": job_id, "phase": "running", "message": "Creating worktree…"}
    )

    if not _CLAUDE_PATH:
        async with session_factory() as session:
            job = await session.get(AgentJob, job_id)
            if job:
                job.status = "failed"
                job.error_message = "Claude CLI not available on this system"
                job.updated_at = utcnow()
                session.add(job)
                await session.commit()
        await _broadcast(
            "agent_progress",
            {"job_id": job_id, "phase": "failed", "message": "Claude CLI not available"},
        )
        return

    worktree_created = False
    events: list[dict] = []

    try:
        # Create git worktree
        wt_proc = await asyncio.create_subprocess_exec(
            "git",
            "worktree",
            "add",
            worktree_path,
            "-b",
            branch_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, wt_stderr = await wt_proc.communicate()
        if wt_proc.returncode != 0:
            raise RuntimeError(f"git worktree add failed: {wt_stderr.decode()[:300]}")
        worktree_created = True

        await _broadcast(
            "agent_progress",
            {
                "job_id": job_id,
                "phase": "running",
                "message": f"Worktree ready on branch {branch_name}",
            },
        )

        prompt = _build_execute_prompt(plan_text)
        proc = await asyncio.create_subprocess_exec(
            _CLAUDE_PATH,
            "-p",
            prompt,
            "--output-format",
            "stream-json",
            "--allowedTools",
            "Edit,Write,Bash(git commit:*),Read,Glob,Grep",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=worktree_path,
        )
        assert proc.stdout is not None
        assert proc.stderr is not None

        stderr_task = asyncio.create_task(_drain(proc.stderr))
        result_summary = ""

        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            line_str = line.decode().strip()
            if not line_str:
                continue
            try:
                event_data = json.loads(line_str)
                events.append(event_data)
                if isinstance(event_data, dict):
                    if event_data.get("type") == "result":
                        result_summary = event_data.get("result", "")
                await _broadcast(
                    "agent_progress", {"job_id": job_id, "phase": "running", "event": event_data}
                )
            except json.JSONDecodeError:
                pass

        await proc.wait()
        stderr_bytes = await stderr_task

        if proc.returncode != 0:
            err_msg = stderr_bytes.decode()[:500]
            raise RuntimeError(f"Claude exited {proc.returncode}: {err_msg}")

        async with session_factory() as session:
            job = await session.get(AgentJob, job_id)
            if job and job.status != "cancelled":
                job.status = "completed"
                job.branch_name = branch_name
                job.result_summary = result_summary.strip()
                job.events_json = json.dumps(events)
                job.updated_at = utcnow()
                session.add(job)
                await session.commit()

        await _broadcast(
            "agent_progress",
            {
                "job_id": job_id,
                "phase": "completed",
                "branch": branch_name,
                "message": "Fix committed successfully",
            },
        )

    except Exception as exc:
        async with session_factory() as session:
            job = await session.get(AgentJob, job_id)
            if job:
                job.status = "failed"
                job.error_message = str(exc)[:500]
                job.events_json = json.dumps(events)
                job.updated_at = utcnow()
                session.add(job)
                await session.commit()
        await _broadcast(
            "agent_progress", {"job_id": job_id, "phase": "failed", "message": str(exc)[:200]}
        )

    finally:
        if worktree_created:
            cleanup = await asyncio.create_subprocess_exec(
                "git",
                "worktree",
                "remove",
                worktree_path,
                "--force",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await cleanup.wait()
