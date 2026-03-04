import hashlib
from datetime import UTC, datetime, timedelta

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.models import TriageItem


def generate_fingerprint(exception_type: str, exception_message: str, source: str) -> str:
    raw = f"{exception_type}{exception_message}{source}"
    return hashlib.sha256(raw.encode()).hexdigest()


def classify_severity(occurrence_count: int, exception_type: str) -> str:
    if occurrence_count > 100 or "fatal" in exception_type.lower():
        return "critical"
    if occurrence_count > 10:
        return "high"
    if occurrence_count > 3:
        return "medium"
    return "low"


async def deduplicate(session: AsyncSession, fingerprint: str) -> TriageItem | None:
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=24)
    result = await session.exec(
        select(TriageItem).where(
            TriageItem.fingerprint == fingerprint,
            TriageItem.first_seen >= cutoff,
        )
    )
    return result.first()
