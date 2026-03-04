"""PostHog error event webhook receiver."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.database import get_session
from clarity_backend.models import TriageItem
from clarity_backend.triage import (
    classify_posthog_severity,
    extract_posthog_title,
    make_posthog_fingerprint,
    safe_metadata,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/posthog", status_code=status.HTTP_200_OK)
async def posthog_webhook(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Receive a PostHog error event, deduplicate by fingerprint, and upsert into triage queue."""
    events: list[dict] = payload.get("batch", [payload])

    if not events:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty payload")

    ingested = 0
    updated = 0

    for event in events:
        fingerprint = make_posthog_fingerprint(event)

        result = await session.exec(select(TriageItem).where(TriageItem.fingerprint == fingerprint))
        existing = result.first()

        if existing:
            existing.occurrence_count += 1
            existing.last_seen = datetime.now(UTC).replace(tzinfo=None)
            session.add(existing)
            updated += 1
        else:
            item = TriageItem(
                source="posthog",
                title=extract_posthog_title(event),
                description=str(event.get("properties", {}).get("$exception_message", "")),
                severity=classify_posthog_severity(event),
                fingerprint=fingerprint,
                metadata_json=safe_metadata(event),
            )
            session.add(item)
            ingested += 1

    await session.commit()
    return {"ingested": ingested, "updated": updated}
