"""Command executors — turn classified intents into database queries and responses."""

from datetime import UTC, datetime, timedelta

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.models import NotificationRecord, TriageItem
from clarity_backend.voice.intent import (
    ARCHIVE_NOTIFICATION,
    CHECK_STATUS,
    CREATE_ISSUE,
    DISMISS_ITEM,
    FIX_ITEM,
    MORNING_BRIEF,
    PLANE_COMPLETE_TASK,
    PLANE_CREATE_TASK,
    PLANE_LIST_TASKS,
    QUERY_ERRORS,
    QUERY_VULNS,
    READ_EMAILS,
    READ_NOTIFICATIONS,
    REPLY_MESSAGE,
    SNOOZE_ITEM,
    UNKNOWN,
    Intent,
)

# Response templates — written for TTS readability
TEMPLATES: dict[str, str] = {
    QUERY_ERRORS: "You have {count} error{s} {timeframe_label}. {severity_note}",
    QUERY_VULNS: "There are {count} vulnerability items {timeframe_label}. {severity_note}",
    CHECK_STATUS: "{pending} items pending, {critical} critical, {actioned} actioned today.",
    CREATE_ISSUE: "Created a Plane issue for item {item_id}.",
    SNOOZE_ITEM: "Snoozed item {item_id}.",
    DISMISS_ITEM: "Dismissed item {item_id}.",
    MORNING_BRIEF: "Morning brief: {errors} new errors, {vulns} new vulnerabilities, {actioned} items actioned yesterday, {pending} still pending.",
    READ_EMAILS: "You have {count} unread email{s}. {detail}",
    READ_NOTIFICATIONS: "You have {count} unread notification{s}. {detail}",
    REPLY_MESSAGE: "I can't compose replies by voice yet. Open the inbox to reply.",
    ARCHIVE_NOTIFICATION: "Archived {count} notification{s}.",
    FIX_ITEM: "Starting a fix for item {item_id}. Claude is generating a plan.",
    PLANE_CREATE_TASK: "I'll create a task in {project_name}: \"{title}\". Priority: {priority}. Please confirm.",
    PLANE_COMPLETE_TASK: "I'll mark {task_ref} as done in {project_name}. Please confirm.",
    PLANE_LIST_TASKS: "You have {count} task{s} in {project_name}. {summary}",
    UNKNOWN: "I didn't understand that. Try asking about errors, vulnerabilities, or your current status.",
}


async def execute(intent: Intent, session: AsyncSession) -> dict:
    """Execute an intent and return a response dict."""
    handler = HANDLERS.get(intent.type, _handle_unknown)
    return await handler(intent, session)


async def _handle_query_errors(intent: Intent, session: AsyncSession) -> dict:
    cutoff = _timeframe_cutoff(intent.params.get("timeframe", "24h"))
    query = select(func.count()).where(
        TriageItem.source == "posthog",
        TriageItem.status == "pending",
        TriageItem.first_seen >= cutoff,
    )
    severity = intent.params.get("severity")
    if severity:
        query = query.where(TriageItem.severity == severity)

    result = await session.exec(query)
    count = result.one()
    sev_note = f"Filtered to {severity} severity." if severity else ""

    return {
        "response": TEMPLATES[QUERY_ERRORS].format(
            count=count,
            s="" if count == 1 else "s",
            timeframe_label=_timeframe_label(intent.params.get("timeframe", "24h")),
            severity_note=sev_note,
        ).strip(),
        "data": {"count": count, "source": "posthog"},
    }


async def _handle_query_vulns(intent: Intent, session: AsyncSession) -> dict:
    cutoff = _timeframe_cutoff(intent.params.get("timeframe", "24h"))
    query = select(func.count()).where(
        TriageItem.source == "aikido",
        TriageItem.status == "pending",
        TriageItem.first_seen >= cutoff,
    )
    result = await session.exec(query)
    count = result.one()

    return {
        "response": TEMPLATES[QUERY_VULNS].format(
            count=count,
            timeframe_label=_timeframe_label(intent.params.get("timeframe", "24h")),
            severity_note="",
        ).strip(),
        "data": {"count": count, "source": "aikido"},
    }


async def _handle_status(intent: Intent, session: AsyncSession) -> dict:
    pending = (await session.exec(
        select(func.count()).where(TriageItem.status == "pending")
    )).one()
    critical = (await session.exec(
        select(func.count()).where(TriageItem.severity == "critical", TriageItem.status == "pending")
    )).one()
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    actioned = (await session.exec(
        select(func.count()).where(TriageItem.status == "actioned", TriageItem.last_seen >= today_start)
    )).one()

    return {
        "response": TEMPLATES[CHECK_STATUS].format(pending=pending, critical=critical, actioned=actioned),
        "data": {"pending": pending, "critical": critical, "actioned": actioned},
    }


async def _handle_morning_brief(intent: Intent, session: AsyncSession) -> dict:
    cutoff_24h = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=24)

    errors = (await session.exec(
        select(func.count()).where(TriageItem.source == "posthog", TriageItem.first_seen >= cutoff_24h)
    )).one()
    vulns = (await session.exec(
        select(func.count()).where(TriageItem.source == "aikido", TriageItem.first_seen >= cutoff_24h)
    )).one()
    actioned = (await session.exec(
        select(func.count()).where(TriageItem.status == "actioned", TriageItem.last_seen >= cutoff_24h)
    )).one()
    pending = (await session.exec(
        select(func.count()).where(TriageItem.status == "pending")
    )).one()

    return {
        "response": TEMPLATES[MORNING_BRIEF].format(errors=errors, vulns=vulns, actioned=actioned, pending=pending),
        "data": {"errors": errors, "vulns": vulns, "actioned": actioned, "pending": pending},
    }


async def _handle_create_issue(intent: Intent, session: AsyncSession) -> dict:
    item_id = intent.params.get("item_id")
    if not item_id:
        return {"response": "Which item should I create an issue for? Say the item number.", "data": {}}
    return {
        "response": TEMPLATES[CREATE_ISSUE].format(item_id=item_id),
        "data": {"item_id": item_id, "action": "create_issue"},
    }


async def _handle_snooze(intent: Intent, session: AsyncSession) -> dict:
    item_id = intent.params.get("item_id")
    if not item_id:
        return {"response": "Which item should I snooze? Say the item number.", "data": {}}
    return {
        "response": TEMPLATES[SNOOZE_ITEM].format(item_id=item_id),
        "data": {"item_id": item_id, "action": "snooze"},
    }


async def _handle_dismiss(intent: Intent, session: AsyncSession) -> dict:
    item_id = intent.params.get("item_id")
    if not item_id:
        return {"response": "Which item should I dismiss? Say the item number.", "data": {}}
    return {
        "response": TEMPLATES[DISMISS_ITEM].format(item_id=item_id),
        "data": {"item_id": item_id, "action": "dismiss"},
    }


async def _handle_read_emails(intent: Intent, session: AsyncSession) -> dict:
    """Count unread emails from Gmail and Outlook sources."""
    rows = (await session.exec(
        select(NotificationRecord.source, func.count()).where(
            NotificationRecord.source.in_(["gmail", "outlook"]),  # type: ignore[attr-defined]
            NotificationRecord.triage_status == "unread",
        ).group_by(NotificationRecord.source)
    )).all()

    breakdown = {src: cnt for src, cnt in rows}
    gmail_only = breakdown.get("gmail", 0)
    outlook_only = breakdown.get("outlook", 0)
    total = gmail_only + outlook_only

    parts = []
    if gmail_only:
        parts.append(f"{gmail_only} from Gmail")
    if outlook_only:
        parts.append(f"{outlook_only} from Outlook")
    detail = ", ".join(parts) if parts else ""

    return {
        "response": TEMPLATES[READ_EMAILS].format(
            count=total, s="" if total == 1 else "s", detail=detail,
        ).strip(),
        "data": {"count": total, "gmail": gmail_only, "outlook": outlook_only},
    }


async def _handle_read_notifications(intent: Intent, session: AsyncSession) -> dict:
    """Count all unread notifications across all sources."""
    rows = (await session.exec(
        select(NotificationRecord.source, func.count()).where(
            NotificationRecord.triage_status == "unread"
        ).group_by(NotificationRecord.source)
    )).all()

    breakdown = {src: cnt for src, cnt in rows if cnt > 0}
    total = sum(breakdown.values())

    parts = [f"{c} from {s.title()}" for s, c in breakdown.items()]
    detail = ", ".join(parts) if parts else "All clear!"

    return {
        "response": TEMPLATES[READ_NOTIFICATIONS].format(
            count=total, s="" if total == 1 else "s", detail=detail,
        ).strip(),
        "data": {"count": total, "breakdown": breakdown},
    }


async def _handle_reply_message(intent: Intent, session: AsyncSession) -> dict:
    return {
        "response": TEMPLATES[REPLY_MESSAGE],
        "data": {"action": "open_inbox"},
    }


async def _handle_archive_notification(intent: Intent, session: AsyncSession) -> dict:
    """Archive all read notifications."""
    from sqlmodel import update as sql_update

    result = await session.exec(
        select(func.count()).where(NotificationRecord.triage_status == "read")
    )
    count = result.one()

    if count > 0:
        await session.exec(
            sql_update(NotificationRecord)
            .where(NotificationRecord.triage_status == "read")
            .values(triage_status="archived")
        )
        await session.commit()

    return {
        "response": TEMPLATES[ARCHIVE_NOTIFICATION].format(
            count=count, s="" if count == 1 else "s",
        ).strip(),
        "data": {"count": count, "action": "archive"},
    }


async def _handle_fix_item(intent: Intent, session: AsyncSession) -> dict:
    import asyncio

    from clarity_backend.agent.models import AgentJob
    from clarity_backend.agent.routes import get_background_session
    from clarity_backend.agent.runner import create_plan

    item_id = intent.params.get("item_id")
    if not item_id:
        return {"response": "Which item should I fix? Say the item number.", "data": {}}

    item = await session.get(TriageItem, item_id)
    if not item:
        return {"response": f"Item {item_id} not found in the triage queue.", "data": {}}

    job = AgentJob(triage_item_id=item_id)
    session.add(job)
    await session.commit()
    await session.refresh(job)

    item_dict = {
        "title": item.title,
        "description": item.description,
        "severity": item.severity,
        "source": item.source,
    }
    asyncio.create_task(create_plan(job.id, get_background_session, item_dict))

    return {
        "response": TEMPLATES[FIX_ITEM].format(item_id=item_id),
        "data": {"item_id": item_id, "job_id": job.id, "action": "fix_item"},
    }


def _get_project_resolver():
    from clarity_backend.settings.manager import get_plane_projects
    from clarity_backend.voice.project_resolver import ProjectResolver

    return ProjectResolver(get_plane_projects())


async def _handle_plane_create_task(intent: Intent, session: AsyncSession) -> dict:
    project_name = intent.params.get("project_name", "")
    task_title = intent.params.get("task_title", "")
    priority = intent.params.get("priority", "none")

    if not project_name:
        return {"response": "Which project should I create the task in?", "data": {}}
    if not task_title:
        return {"response": f"What should the task be called in {project_name}?", "data": {}}

    resolver = _get_project_resolver()
    result = resolver.resolve(project_name)

    # If offline resolution fails, try AI fallback
    if not result.project_id and not result.alternatives:
        result = await resolver.resolve_with_ai(project_name, task_title)

    if not result.project_id:
        if result.alternatives:
            names = ", ".join(a["name"] for a in result.alternatives[:3])
            return {"response": f"Did you mean {names}?", "data": {"alternatives": result.alternatives}}
        return {"response": f"I don't know a project called {project_name}. Sync your projects in Settings.", "data": {}}

    return {
        "response": TEMPLATES[PLANE_CREATE_TASK].format(
            project_name=result.project_name, title=task_title, priority=priority
        ),
        "data": {
            "pending_action": {
                "action_type": "create_task",
                "project_id": result.project_id,
                "project_name": result.project_name,
                "title": task_title,
                "priority": priority,
            }
        },
    }


async def _handle_plane_complete_task(intent: Intent, session: AsyncSession) -> dict:
    task_ref = intent.params.get("task_ref", "")
    if not task_ref:
        return {"response": "Which task should I complete? Say the task identifier.", "data": {}}

    # Try to parse project identifier and sequence number from task_ref
    # e.g., "acme-42" or "ACME-42" or just "42 in acme"
    import re

    ref_match = re.match(r"([a-zA-Z]+)[- ](\d+)", task_ref)
    if ref_match:
        project_prefix = ref_match.group(1)
        seq_id = int(ref_match.group(2))

        # Resolve prefix to project
        resolver = _get_project_resolver()
        result = resolver.resolve(project_prefix)

        if result.project_id:
            return {
                "response": TEMPLATES[PLANE_COMPLETE_TASK].format(
                    task_ref=task_ref.upper(), project_name=result.project_name
                ),
                "data": {
                    "pending_action": {
                        "action_type": "complete_task",
                        "project_id": result.project_id,
                        "project_name": result.project_name,
                        "task_ref": task_ref.upper(),
                        "sequence_id": seq_id,
                    }
                },
            }

    return {
        "response": f"I couldn't parse the task reference '{task_ref}'. Use the format PROJECT-NUMBER, like ACME-42.",
        "data": {},
    }


async def _handle_plane_list_tasks(intent: Intent, session: AsyncSession) -> dict:
    from clarity_backend.integrations.plane import PlaneClient
    from clarity_backend.config import settings as env_settings
    from clarity_backend.settings.manager import _read_settings, get_plane_projects

    project_name = intent.params.get("project_name")
    s = _read_settings()
    api_key = s.get("plane_api_key") or env_settings.PLANE_API_KEY
    workspace = s.get("plane_workspace_slug") or env_settings.PLANE_WORKSPACE_SLUG

    if not api_key or not workspace:
        return {"response": "Plane is not configured. Set up your API key in Settings.", "data": {}}

    client = PlaneClient(api_key=api_key, workspace_slug=workspace, base_url=env_settings.PLANE_API_URL)

    if project_name:
        resolver = _get_project_resolver()
        result = resolver.resolve(project_name)
        if not result.project_id:
            return {"response": f"I don't know a project called {project_name}.", "data": {}}
        try:
            items = await client.list_work_items(result.project_id, limit=5)
            count = len(items)
            summary = ". ".join(item.get("name", "Untitled")[:60] for item in items[:3])
            return {
                "response": TEMPLATES[PLANE_LIST_TASKS].format(
                    count=count, s="" if count == 1 else "s",
                    project_name=result.project_name, summary=summary or "No tasks."
                ),
                "data": {"tasks": items, "project_name": result.project_name},
            }
        except Exception as e:
            return {"response": f"Failed to fetch tasks: {e}", "data": {}}
    else:
        # Show tasks across all projects — just count from first configured project
        projects = get_plane_projects()
        if not projects:
            return {"response": "No projects configured. Sync your projects in Settings.", "data": {}}

        total = 0
        summaries = []
        for alias, info in list(projects.items())[:3]:
            try:
                items = await client.list_work_items(info["id"], limit=5)
                total += len(items)
                if items:
                    summaries.append(f"{info.get('name', alias)}: {len(items)} tasks")
            except Exception:
                continue

        summary = ". ".join(summaries) if summaries else "No tasks found."
        return {
            "response": f"You have {total} task{'s' if total != 1 else ''} across your projects. {summary}",
            "data": {"total": total},
        }


async def _handle_unknown(intent: Intent, session: AsyncSession) -> dict:
    return {"response": TEMPLATES[UNKNOWN], "data": {}}


HANDLERS = {
    QUERY_ERRORS: _handle_query_errors,
    QUERY_VULNS: _handle_query_vulns,
    CHECK_STATUS: _handle_status,
    MORNING_BRIEF: _handle_morning_brief,
    CREATE_ISSUE: _handle_create_issue,
    SNOOZE_ITEM: _handle_snooze,
    DISMISS_ITEM: _handle_dismiss,
    READ_EMAILS: _handle_read_emails,
    READ_NOTIFICATIONS: _handle_read_notifications,
    REPLY_MESSAGE: _handle_reply_message,
    ARCHIVE_NOTIFICATION: _handle_archive_notification,
    FIX_ITEM: _handle_fix_item,
    PLANE_CREATE_TASK: _handle_plane_create_task,
    PLANE_COMPLETE_TASK: _handle_plane_complete_task,
    PLANE_LIST_TASKS: _handle_plane_list_tasks,
    UNKNOWN: _handle_unknown,
}


def _timeframe_cutoff(timeframe: str) -> datetime:
    now = datetime.now(UTC).replace(tzinfo=None)
    if timeframe == "7d":
        return now - timedelta(days=7)
    if timeframe == "yesterday":
        return now - timedelta(days=1)
    return now - timedelta(hours=24)


def _timeframe_label(timeframe: str) -> str:
    if timeframe == "7d":
        return "in the last week"
    if timeframe == "yesterday":
        return "since yesterday"
    return "in the last 24 hours"
