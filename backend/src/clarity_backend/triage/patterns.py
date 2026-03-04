"""Pattern detection — identify recurring error fingerprints."""

from datetime import UTC, datetime, timedelta

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.models import TriageItem

RECURRENCE_THRESHOLD = 3
RECURRENCE_WINDOW_DAYS = 7


async def get_recurring_fingerprints(session: AsyncSession) -> dict[str, int]:
    """Return fingerprints that appear 3+ times in the last 7 days.

    Returns a dict of {fingerprint: occurrence_count}.
    """
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=RECURRENCE_WINDOW_DAYS)

    result = await session.exec(
        select(TriageItem.fingerprint, func.count(TriageItem.id))
        .where(TriageItem.first_seen >= cutoff, TriageItem.fingerprint != "")
        .group_by(TriageItem.fingerprint)
        .having(func.count(TriageItem.id) >= RECURRENCE_THRESHOLD)
    )

    return {row[0]: row[1] for row in result.all()}


async def is_recurring(session: AsyncSession, fingerprint: str) -> bool:
    """Check if a specific fingerprint is recurring (3+ in 7 days)."""
    if not fingerprint:
        return False

    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=RECURRENCE_WINDOW_DAYS)

    result = await session.exec(
        select(func.count()).where(
            TriageItem.fingerprint == fingerprint,
            TriageItem.first_seen >= cutoff,
        )
    )
    count = result.one()
    return count >= RECURRENCE_THRESHOLD
