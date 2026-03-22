import json
from datetime import UTC, datetime

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.models import NotificationRecord, TokenStore
from clarity_backend.notifications.models import Notification


async def save_notification(session: AsyncSession, notification: Notification) -> None:
    """Save or update a notification, deduplicating by (source, source_id)."""
    result = await session.exec(
        select(NotificationRecord).where(
            NotificationRecord.source == notification.source.value,
            NotificationRecord.source_id == notification.source_id,
        )
    )
    existing = result.first()

    if existing:
        existing.title = notification.title
        existing.body = notification.body
        existing.timestamp = notification.timestamp
        existing.priority = notification.priority.value
        session.add(existing)
    else:
        record = NotificationRecord(
            id=notification.id,
            source=notification.source.value,
            source_account=notification.source_account,
            source_id=notification.source_id,
            notification_type=notification.notification_type.value,
            title=notification.title,
            body=notification.body,
            sender_name=notification.sender_name,
            sender_avatar=notification.sender_avatar,
            timestamp=notification.timestamp,
            priority=notification.priority.value,
            triage_status=notification.triage_status.value,
            is_actionable=notification.is_actionable,
            thread_id=notification.thread_id,
            channel_name=notification.channel_name,
            project_name=notification.project_name,
            raw_payload=json.dumps(notification.raw_payload) if notification.raw_payload else None,
        )
        session.add(record)

    await session.commit()


async def update_triage_status(
    session: AsyncSession,
    notification_id: str,
    status: str,
    snoozed_until: datetime | None = None,
) -> bool:
    record = await session.get(NotificationRecord, notification_id)
    if not record:
        return False
    record.triage_status = status
    if snoozed_until:
        record.snoozed_until = snoozed_until
    session.add(record)
    await session.commit()
    return True


def auto_unsnooze(record: NotificationRecord, now: datetime | None = None) -> bool:
    """If a snoozed record has expired, reset to unread. Returns True if mutated."""
    if record.triage_status != "snoozed" or not record.snoozed_until:
        return False
    snoozed_at = record.snoozed_until
    if snoozed_at.tzinfo is None:
        snoozed_at = snoozed_at.replace(tzinfo=UTC)
    if snoozed_at <= (now or datetime.now(UTC)):
        record.triage_status = "unread"
        record.snoozed_until = None
        return True
    return False


async def load_notifications(
    session: AsyncSession, limit: int = 50, offset: int = 0, status_filter: str | None = None
) -> list[dict]:
    query = select(NotificationRecord).order_by(NotificationRecord.timestamp.desc())  # type: ignore[attr-defined]
    if status_filter:
        query = query.where(NotificationRecord.triage_status == status_filter)
    else:
        query = query.where(NotificationRecord.triage_status != "archived")
    query = query.offset(offset).limit(limit)
    result = await session.exec(query)
    records = result.all()

    now = datetime.now(UTC)
    notifications = []
    dirty = False
    for r in records:
        if auto_unsnooze(r, now):
            session.add(r)
            dirty = True
        notifications.append(_record_to_dict(r))

    if dirty:
        await session.commit()
    return notifications


async def get_notification_by_id(session: AsyncSession, notification_id: str) -> dict | None:
    """Fetch a single notification record by ID."""
    record = await session.get(NotificationRecord, notification_id)
    if not record:
        return None
    if auto_unsnooze(record, datetime.now(UTC)):
        session.add(record)
        await session.commit()
    return _record_to_dict(record)


async def search_notifications(
    session: AsyncSession, query: str, limit: int = 50, offset: int = 0
) -> list[dict]:
    """Search notifications by title, body, or sender_name (case-insensitive)."""
    query_lower = query.lower()
    stmt = (
        select(NotificationRecord)
        .where(
            NotificationRecord.triage_status != "archived",
            (func.lower(NotificationRecord.title).contains(query_lower))
            | (func.lower(NotificationRecord.body).contains(query_lower))
            | (func.lower(NotificationRecord.sender_name).contains(query_lower)),
        )
        .order_by(NotificationRecord.timestamp.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.exec(stmt)
    return [_record_to_dict(r) for r in result.all()]


async def get_accounts_by_service(session: AsyncSession, service: str) -> list[dict]:
    result = await session.exec(select(TokenStore).where(TokenStore.service == service))
    records = result.all()
    return [
        {
            "account": r.account,
            "access_token": r.access_token,
            "refresh_token": r.refresh_token,
        }
        for r in records
    ]


async def delete_account_tokens(session: AsyncSession, service: str, account: str) -> bool:
    token_id = f"{service}:{account}"
    record = await session.get(TokenStore, token_id)
    if not record:
        return False
    await session.delete(record)
    await session.commit()
    return True


def _record_to_dict(r: NotificationRecord) -> dict:
    return {
        "id": r.id,
        "source": r.source,
        "source_account": r.source_account,
        "source_id": r.source_id,
        "notification_type": r.notification_type,
        "title": r.title,
        "body": r.body,
        "sender_name": r.sender_name,
        "sender_avatar": r.sender_avatar,
        "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        "priority": r.priority,
        "triage_status": r.triage_status,
        "is_actionable": r.is_actionable,
        "thread_id": r.thread_id,
        "channel_name": r.channel_name,
        "project_name": r.project_name,
        "snoozed_until": r.snoozed_until.isoformat() if r.snoozed_until else None,
        "raw_payload": json.loads(r.raw_payload) if r.raw_payload else None,
    }
