from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.database import get_session
from clarity_backend.notifications.crud import load_notifications, update_triage_status
from clarity_backend.notifications.models import NotificationAction, TaskCreate
from clarity_backend.notifications.ws import ws_manager

router = APIRouter(prefix="/api", tags=["notifications"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/notifications")
async def get_notifications(session: SessionDep, limit: int = 50, status: str | None = None):
    notifications = await load_notifications(session, limit=limit, status_filter=status)
    return {"notifications": notifications}


@router.post("/notifications/{notification_id}/action")
async def action_notification(notification_id: str, action: NotificationAction, session: SessionDep):
    if action.action == "reply":
        payload = action.payload or {}
        body = payload.get("body", "")
        source = payload.get("source")
        account = payload.get("source_account")
        if not source or not body or not account:
            raise HTTPException(400, "Reply requires 'source', 'source_account', and 'body' in payload")

        from clarity_backend.notifications.models import Source
        from clarity_backend.services.registry import registry

        try:
            source_enum = Source(source)
        except ValueError as err:
            raise HTTPException(400, f"Invalid source: {source}") from err
        service = registry.get_service_for_reply(source_enum, account)
        if not service:
            raise HTTPException(404, f"No service found for {source}:{account}")
        success = await service.reply(payload.get("source_id", notification_id), body)
        if not success:
            raise HTTPException(500, "Reply failed")
        return {"status": "replied"}

    elif action.action == "archive":
        updated = await update_triage_status(session, notification_id, "archived")
        if not updated:
            raise HTTPException(404, f"Notification {notification_id} not found")
        await ws_manager.send_update(notification_id, {"triage_status": "archived"})
        return {"status": "archived"}

    elif action.action == "mark_read":
        updated = await update_triage_status(session, notification_id, "read")
        if not updated:
            raise HTTPException(404, f"Notification {notification_id} not found")
        await ws_manager.send_update(notification_id, {"triage_status": "read"})
        return {"status": "read"}

    elif action.action == "snooze":
        minutes = (action.payload or {}).get("snooze_minutes", 30)
        snoozed_until = datetime.now(UTC) + timedelta(minutes=minutes)
        updated = await update_triage_status(session, notification_id, "snoozed", snoozed_until=snoozed_until)
        if not updated:
            raise HTTPException(404, f"Notification {notification_id} not found")
        await ws_manager.send_update(notification_id, {"triage_status": "snoozed", "snooze_minutes": minutes})
        return {"status": "snoozed", "minutes": minutes}

    else:
        raise HTTPException(400, f"Unknown action: {action.action}")


@router.post("/tasks")
async def create_task(task: TaskCreate):
    from clarity_backend.services.registry import registry

    if task.target == "plane" and registry.plane_service:
        result = await registry.plane_service.create_issue(
            title=task.title,
            description=task.description or "",
            priority=task.priority.value,
            project_id=task.project_id,
        )
        if result:
            return {"status": "created", "target": "plane", "issue": result}
        raise HTTPException(500, "Failed to create Plane issue")

    elif task.target == "asana" and registry.asana_service:
        result = await registry.asana_service.create_task(
            title=task.title,
            description=task.description or "",
            project_gid=task.project_id,
        )
        if result:
            return {"status": "created", "target": "asana", "task": result}
        raise HTTPException(500, "Failed to create Asana task")

    else:
        raise HTTPException(400, f"Target '{task.target}' is not configured")


@router.get("/services/status")
async def services_status():
    from clarity_backend.services.registry import registry

    return {
        "services": [
            {"service": s.source.value, "connected": s.is_connected, "account": s.account}
            for s in registry.services
        ]
    }


@router.get("/auth/status")
async def auth_status():
    from clarity_backend.services.registry import registry

    gmail_accounts = [
        {"email": svc.email, "connected": svc.is_connected and svc._credentials is not None}
        for svc in registry.gmail_services
    ]
    outlook_accounts = [
        {"email": svc.email, "connected": svc.is_connected and svc._credentials is not None}
        for svc in registry.outlook_services
    ]
    return {"gmail_accounts": gmail_accounts, "outlook_accounts": outlook_accounts}
