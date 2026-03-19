"""Clarity App webhook receiver — ingests events as notifications."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.database import get_session
from clarity_backend.notifications.crud import save_notification
from clarity_backend.notifications.models import (
    Notification,
    NotificationType,
    Priority,
    Source,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Maps Clarity event_type to (NotificationType, Priority)
EVENT_MAP: dict[str, tuple[NotificationType, Priority]] = {
    "schedule_status_change": (NotificationType.SCHEDULE_UPDATE, Priority.NORMAL),
    "action_point_created": (NotificationType.ACTION_POINT, Priority.HIGH),
    "review_overdue": (NotificationType.COMPLIANCE_ALERT, Priority.URGENT),
    "registration_submitted": (NotificationType.SCHEDULE_UPDATE, Priority.NORMAL),
    "compliance_failed": (NotificationType.COMPLIANCE_ALERT, Priority.HIGH),
}


def _get_webhook_secret() -> str:
    from clarity_backend.config import settings as env_settings
    from clarity_backend.settings.manager import _read_settings

    s = _read_settings()
    return s.get("clarity_webhook_secret") or env_settings.CLARITY_WEBHOOK_SECRET


@router.post("/clarity", status_code=status.HTTP_200_OK)
async def clarity_webhook(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_session),
    x_webhook_secret: str | None = Header(default=None),
) -> dict[str, Any]:
    """Receive an event from Clarity App and create a notification."""
    secret = _get_webhook_secret()
    if secret and x_webhook_secret != secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    event_type = payload.get("event_type", "")
    if not event_type:
        raise HTTPException(status_code=400, detail="Missing event_type")

    mapping = EVENT_MAP.get(event_type)
    if not mapping:
        logger.warning("Unknown Clarity event_type: %s", event_type)
        return {"ingested": 0, "skipped": event_type}

    notification_type, priority = mapping

    title = payload.get("title", f"Clarity: {event_type}")
    body = payload.get("body", payload.get("description", ""))
    source_id = payload.get("id", payload.get("event_id", event_type))

    notification = Notification(
        source=Source.CLARITY,
        source_account="clarity-app",
        source_id=str(source_id),
        notification_type=notification_type,
        title=title,
        body=body,
        sender_name="Clarity App",
        priority=priority,
        project_name=payload.get("project_name"),
        raw_payload=payload,
    )

    await save_notification(session, notification)

    # Broadcast to WebSocket clients
    from clarity_backend.notifications.ws import ws_manager

    await ws_manager.send_notification(notification)

    return {"ingested": 1}
