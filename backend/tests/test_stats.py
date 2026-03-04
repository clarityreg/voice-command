"""Tests for the statistics module."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.models import TriageItem
from clarity_backend.stats.queries import (
    avg_time_to_triage_hours,
    daily_actioned_trend,
    get_severity_breakdown,
    weekly_resolved_count,
)


async def _seed(session: AsyncSession, **overrides) -> TriageItem:
    defaults = {
        "source": "posthog",
        "title": "Test Error",
        "description": "Desc",
        "severity": "medium",
        "status": "pending",
        "fingerprint": f"fp-{id(overrides)}",
        "occurrence_count": 1,
        "first_seen": datetime.now(UTC) - timedelta(hours=2),
        "last_seen": datetime.now(UTC),
        "metadata_json": "{}",
    }
    defaults.update(overrides)
    item = TriageItem(**defaults)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@pytest.mark.asyncio
async def test_weekly_resolved_empty(db_session: AsyncSession):
    assert await weekly_resolved_count(db_session) == 0


@pytest.mark.asyncio
async def test_weekly_resolved_counts_recent(db_session: AsyncSession):
    await _seed(db_session, status="actioned", fingerprint="fp1")
    await _seed(db_session, status="actioned", fingerprint="fp2")
    await _seed(db_session, status="pending", fingerprint="fp3")
    assert await weekly_resolved_count(db_session) == 2


@pytest.mark.asyncio
async def test_weekly_resolved_ignores_old(db_session: AsyncSession):
    await _seed(
        db_session,
        status="actioned",
        last_seen=datetime.now(UTC) - timedelta(days=10),
        fingerprint="fp-old",
    )
    assert await weekly_resolved_count(db_session) == 0


@pytest.mark.asyncio
async def test_avg_triage_hours_none_when_empty(db_session: AsyncSession):
    assert await avg_time_to_triage_hours(db_session) is None


@pytest.mark.asyncio
async def test_avg_triage_hours_calculates(db_session: AsyncSession):
    now = datetime.now(UTC)
    await _seed(
        db_session,
        status="actioned",
        first_seen=now - timedelta(hours=4),
        last_seen=now,
        fingerprint="fp-fast",
    )
    result = await avg_time_to_triage_hours(db_session)
    assert result is not None
    assert 3.5 <= result <= 4.5


@pytest.mark.asyncio
async def test_daily_trend_fills_zeros(db_session: AsyncSession):
    trend = await daily_actioned_trend(db_session, days=7)
    assert len(trend) == 7
    assert all(p["count"] == 0 for p in trend)


@pytest.mark.asyncio
async def test_severity_breakdown(db_session: AsyncSession):
    await _seed(db_session, severity="critical", status="pending", fingerprint="fp-c")
    await _seed(db_session, severity="critical", status="pending", fingerprint="fp-c2")
    await _seed(db_session, severity="low", status="pending", fingerprint="fp-l")
    await _seed(db_session, severity="high", status="actioned", fingerprint="fp-h")  # not pending
    breakdown = await get_severity_breakdown(db_session)
    assert breakdown["critical"] == 2
    assert breakdown["low"] == 1
    assert breakdown["high"] == 0
    assert breakdown["medium"] == 0


@pytest.mark.asyncio
async def test_stats_endpoint(client: AsyncClient):
    resp = await client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "weekly_resolved" in data
    assert "avg_triage_hours" in data
    assert "trend" in data
    assert "severity_breakdown" in data
    assert isinstance(data["trend"], list)
