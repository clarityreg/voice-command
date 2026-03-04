"""Unified triage view — combines error/vuln triage items with actionable notifications."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.database import get_session
from clarity_backend.models import NotificationRecord, TriageItem
from clarity_backend.notifications.crud import auto_unsnooze
from clarity_backend.notifications.models import Source

router = APIRouter(prefix="/api/triage", tags=["triage-unified"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/unified")
async def get_unified_triage(
    session: SessionDep,
    source: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    """Return both TriageItems and actionable/unread NotificationRecords in a common format."""
    items: list[dict] = []

    max_rows = offset + limit

    # 1. Fetch pending triage items (errors and vulnerabilities)
    triage_query = select(TriageItem).where(TriageItem.status == "pending")
    if source and source in ("posthog", "aikido"):
        triage_query = triage_query.where(TriageItem.source == source)
    triage_query = triage_query.order_by(TriageItem.last_seen.desc()).limit(max_rows)  # type: ignore[attr-defined]
    triage_result = await session.exec(triage_query)

    for item in triage_result.all():
        items.append({
            "id": str(item.id),
            "kind": "triage",
            "source": item.source,
            "title": item.title,
            "description": item.description,
            "severity": item.severity,
            "status": item.status,
            "timestamp": item.last_seen.isoformat() if item.last_seen else None,
            "occurrence_count": item.occurrence_count,
            "fingerprint": item.fingerprint,
        })

    # 2. Fetch unread/actionable notifications
    notif_sources = [s.value for s in Source]
    if source and source in notif_sources:
        notif_sources = [source]
    elif source and source not in notif_sources:
        notif_sources = []

    dirty = False
    if notif_sources:
        notif_query = (
            select(NotificationRecord)
            .where(
                NotificationRecord.triage_status.in_(["unread", "read"]),  # type: ignore[attr-defined]
                NotificationRecord.source.in_(notif_sources),  # type: ignore[attr-defined]
            )
            .order_by(NotificationRecord.timestamp.desc())  # type: ignore[attr-defined]
            .limit(max_rows)
        )
        notif_result = await session.exec(notif_query)

        for n in notif_result.all():
            if auto_unsnooze(n):
                session.add(n)
                dirty = True

            items.append({
                "id": n.id,
                "kind": "notification",
                "source": n.source,
                "title": n.title,
                "description": n.body,
                "severity": _priority_to_severity(n.priority),
                "status": n.triage_status,
                "timestamp": n.timestamp.isoformat() if n.timestamp else None,
                "sender_name": n.sender_name,
                "notification_type": n.notification_type,
                "is_actionable": n.is_actionable,
            })

    if dirty:
        await session.commit()

    # Sort by timestamp descending
    items.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    return items[offset : offset + limit]


def _priority_to_severity(priority: str) -> str:
    """Map notification priority to triage severity for unified display."""
    return {
        "urgent": "critical",
        "high": "high",
        "normal": "medium",
        "low": "low",
    }.get(priority, "low")
