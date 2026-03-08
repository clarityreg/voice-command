"""PostHog polling service — fetches error events and feeds them into the triage queue."""

import asyncio
from datetime import UTC, datetime

import httpx
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.config import settings
from clarity_backend.database import engine
from clarity_backend.models import TriageItem
from clarity_backend.notifications.models import (
    Notification,
    NotificationType,
    Priority,
    Source,
)
from clarity_backend.services.base import BaseService
from clarity_backend.triage import (
    classify_posthog_severity,
    extract_posthog_title,
    make_posthog_fingerprint,
    safe_metadata,
)

def _normalize_event(event: dict) -> dict:
    """Normalize events API format to match webhook format expected by triage helpers.

    Events API uses $exception_list, $exception_types, $exception_values, $exception_level.
    Webhook format uses $exception_type, $exception_message, $level.
    """
    props = event.get("properties", {})
    if "$exception_type" in props:
        return event  # already in webhook format

    exc_list = props.get("$exception_list", [])
    first = exc_list[0] if exc_list else {}

    exc_type = first.get("type") or ""
    if not exc_type:
        types = props.get("$exception_types", [])
        exc_type = types[0] if types else "UnknownError"

    exc_message = first.get("value") or ""
    if not exc_message:
        values = props.get("$exception_values", [])
        exc_message = values[0] if values else ""

    level = props.get("$exception_level", props.get("$level", ""))

    normalized = dict(event)
    normalized["properties"] = {
        **props,
        "$exception_type": exc_type,
        "$exception_message": exc_message,
        "$level": level,
    }
    return normalized


_SEVERITY_TO_PRIORITY = {
    "critical": Priority.URGENT,
    "high": Priority.HIGH,
    "medium": Priority.NORMAL,
    "low": Priority.LOW,
}


class PostHogPollerService(BaseService):
    def __init__(self):
        super().__init__(Source.POSTHOG, "PostHog")
        self._host = settings.POSTHOG_HOST.rstrip("/")
        self._project_id = settings.POSTHOG_PROJECT_ID
        self._headers = {"Authorization": f"Bearer {settings.POSTHOG_API_KEY}"}
        self._poll_interval = settings.POSTHOG_POLL_INTERVAL
        self._last_check: datetime | None = None

    @property
    def _configured(self) -> bool:
        return bool(settings.POSTHOG_API_KEY and self._project_id)

    async def connect(self) -> bool:
        if not self._configured:
            print("[PostHog] Skipping — API key or project ID not set")
            return False
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self._host}/api/projects/{self._project_id}/",
                    headers=self._headers,
                )
                resp.raise_for_status()
                name = resp.json().get("name", self._project_id)
                print(f"[PostHog] Connected to project: {name}")
                return True
        except Exception as e:
            print(f"[PostHog] Connection error: {e}")
            return False

    async def disconnect(self):
        pass

    async def fetch_recent(self, limit: int = 20) -> list[Notification]:
        if not self._configured:
            return []
        events = await self._fetch_events(limit=limit)
        return [self._event_to_notification(e) for e in events]

    async def listen(self):
        if not self._configured:
            return
        while self._running:
            try:
                after = self._last_check.isoformat() if self._last_check else None
                events = await self._fetch_events(limit=50, after=after)
                if events:
                    await self._upsert_triage_items(events)
                    for event in events:
                        await self.emit_notification(self._event_to_notification(event))
                self._last_check = datetime.now(UTC)
            except Exception as e:
                print(f"[PostHog] Polling error: {e}")
            await asyncio.sleep(self._poll_interval)

    async def _fetch_events(
        self, limit: int = 50, after: str | None = None
    ) -> list[dict]:
        params: dict = {
            "event": "$exception",
            "limit": limit,
            "order_by": ["-timestamp"],
        }
        if after:
            params["after"] = after
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self._host}/api/projects/{self._project_id}/events/",
                    headers=self._headers,
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()
                return [_normalize_event(e) for e in data.get("results", [])]
        except Exception as e:
            print(f"[PostHog] Error fetching events: {e}")
            return []

    async def _upsert_triage_items(self, events: list[dict]) -> None:
        async with AsyncSession(engine) as session:
            for event in events:
                fingerprint = make_posthog_fingerprint(event)
                result = await session.exec(
                    select(TriageItem).where(TriageItem.fingerprint == fingerprint)
                )
                existing = result.first()
                if existing:
                    existing.occurrence_count += 1
                    existing.last_seen = datetime.now(UTC).replace(tzinfo=None)
                    session.add(existing)
                else:
                    props = event.get("properties", {})
                    item = TriageItem(
                        source="posthog",
                        title=extract_posthog_title(event),
                        description=str(props.get("$exception_message", "")),
                        severity=classify_posthog_severity(event),
                        fingerprint=fingerprint,
                        metadata_json=safe_metadata(event),
                    )
                    session.add(item)
            await session.commit()

    def _event_to_notification(self, event: dict) -> Notification:
        props = event.get("properties", {})
        severity = classify_posthog_severity(event)
        priority = _SEVERITY_TO_PRIORITY.get(severity, Priority.NORMAL)
        ts_raw = event.get("timestamp", "")
        try:
            timestamp = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            timestamp = datetime.now(UTC)

        exc_type = props.get("$exception_type", "UnknownError")
        exc_message = props.get("$exception_message", "")
        current_url = props.get("$current_url", "")
        distinct_id = event.get("distinct_id", "")

        # Title = exception type (like PostHog's error tracking UI)
        # Body = message + context
        body_parts = []
        if exc_message:
            body_parts.append(exc_message)
        if current_url:
            body_parts.append(f"URL: {current_url}")
        if distinct_id:
            body_parts.append(f"User: {distinct_id}")

        return Notification(
            source=Source.POSTHOG,
            source_account="PostHog",
            source_id=event.get("uuid", event.get("id", "")),
            notification_type=NotificationType.TASK_UPDATE,
            title=exc_type,
            body="\n".join(body_parts)[:500],
            sender_name="PostHog",
            priority=priority,
            timestamp=timestamp,
            raw_payload={
                "distinct_id": distinct_id,
                "current_url": current_url,
                "exception_type": exc_type,
                "exception_message": exc_message,
                "exception_level": props.get("$level", ""),
                "issue_id": props.get("$exception_issue_id", ""),
                "occurrences": props.get("$exception_fingerprint_record", []),
            },
        )
