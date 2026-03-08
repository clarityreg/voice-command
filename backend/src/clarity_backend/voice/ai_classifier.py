"""AI-powered intent classifier using local Ollama LLM.

Tier 2 fallback — called only when the regex classifier returns UNKNOWN.
Degrades gracefully when Ollama is not running (returns None).
"""

import json

import httpx

from clarity_backend.voice.intent import Intent

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"

SYSTEM_PROMPT = """You are a voice command classifier for a task management app. Given a transcript, output JSON:
{{"intent": "<type>", "params": {{"project_name": "...", "task_title": "...", "priority": "...", "task_ref": "..."}}}}}

Intent types:
- plane_create_task: user wants to create a new task/ticket in a project
- plane_complete_task: user wants to mark a task as done/complete
- plane_list_tasks: user wants to see their tasks
- query_errors: user asks about errors/bugs/exceptions
- query_vulns: user asks about vulnerabilities/security
- check_status: user asks for status/overview
- morning_brief: user wants a daily summary/digest
- unknown: you cannot determine the intent

Available projects: {project_list}

Only include params that are clearly mentioned. Use "none" for unspecified priority.
Output ONLY valid JSON, nothing else."""


async def classify_with_ai(text: str, project_names: list[str]) -> Intent | None:
    """Attempt classification via local Ollama. Returns None if unavailable."""
    project_list = ", ".join(project_names) if project_names else "none configured"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": f"Classify this voice command: \"{text}\"",
                    "system": SYSTEM_PROMPT.format(project_list=project_list),
                    "stream": False,
                    "format": "json",
                },
            )
            if resp.status_code != 200:
                return None

            body = resp.json()
            raw = body.get("response", "")
            parsed = json.loads(raw)

            intent_type = parsed.get("intent", "unknown")
            params = parsed.get("params", {})
            # Clean out empty params
            params = {k: v for k, v in params.items() if v}

            if intent_type == "unknown":
                return None

            return Intent(type=intent_type, confidence=0.7, params=params)

    except (httpx.ConnectError, httpx.TimeoutException):
        return None
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
