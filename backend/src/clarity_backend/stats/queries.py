"""Statistics queries for triage metrics."""

from datetime import UTC, datetime, timedelta

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.models import TriageItem


async def weekly_resolved_count(session: AsyncSession) -> int:
    """Count items actioned in the past 7 days."""
    cutoff = datetime.now(UTC) - timedelta(days=7)
    result = await session.exec(
        select(func.count()).where(
            TriageItem.status == "actioned",
            TriageItem.last_seen >= cutoff,
        )
    )
    return result.one()


async def avg_time_to_triage_hours(session: AsyncSession) -> float | None:
    """Average hours from first_seen to last_seen for actioned items (past 30 days).

    Returns None if no actioned items exist.
    """
    cutoff = datetime.now(UTC) - timedelta(days=30)
    result = await session.exec(
        select(TriageItem.first_seen, TriageItem.last_seen).where(
            TriageItem.status == "actioned",
            TriageItem.last_seen >= cutoff,
        )
    )
    rows = result.all()
    if not rows:
        return None

    total_hours = 0.0
    for first_seen, last_seen in rows:
        delta = (last_seen - first_seen).total_seconds() / 3600
        total_hours += max(delta, 0)
    return round(total_hours / len(rows), 1)


async def daily_actioned_trend(session: AsyncSession, days: int = 14) -> list[dict]:
    """Return per-day actioned counts for the past N days.

    Returns a list of {"date": "YYYY-MM-DD", "count": int} dicts.
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)
    result = await session.exec(
        select(TriageItem.last_seen).where(
            TriageItem.status == "actioned",
            TriageItem.last_seen >= cutoff,
        )
    )
    rows = result.all()

    # Bucket by date
    counts: dict[str, int] = {}
    for last_seen in rows:
        day_key = last_seen.strftime("%Y-%m-%d")
        counts[day_key] = counts.get(day_key, 0) + 1

    # Fill in zero days
    trend = []
    today = datetime.now(UTC).date()
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.isoformat()
        trend.append({"date": day_str, "count": counts.get(day_str, 0)})

    return trend


async def get_severity_breakdown(session: AsyncSession) -> dict[str, int]:
    """Count pending items grouped by severity (single query)."""
    result = await session.exec(
        select(TriageItem.severity, func.count())
        .where(  # type: ignore[call-overload]
            TriageItem.status == "pending",
        )
        .group_by(TriageItem.severity)
    )
    counts = dict(result.all())
    # Ensure all four levels are present
    return {sev: counts.get(sev, 0) for sev in ("critical", "high", "medium", "low")}
