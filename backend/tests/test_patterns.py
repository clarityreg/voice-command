"""Tests for pattern detection — recurring fingerprints."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.models import TriageItem
from clarity_backend.triage.patterns import get_recurring_fingerprints, is_recurring


async def _seed(
    session: AsyncSession,
    fingerprint: str,
    hours_ago: int = 1,
    status: str = "pending",
) -> TriageItem:
    now = datetime.now(UTC).replace(tzinfo=None)
    item = TriageItem(
        source="posthog",
        title=f"Error {fingerprint}",
        severity="high",
        status=status,
        fingerprint=fingerprint,
        first_seen=now - timedelta(hours=hours_ago),
        last_seen=now,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@pytest.mark.asyncio
async def test_no_recurring_when_below_threshold(db_session: AsyncSession):
    await _seed(db_session, "fp-abc", hours_ago=1)
    await _seed(db_session, "fp-abc", hours_ago=2)
    # Only 2 occurrences — below threshold of 3
    result = await get_recurring_fingerprints(db_session)
    assert "fp-abc" not in result


@pytest.mark.asyncio
async def test_recurring_at_threshold(db_session: AsyncSession):
    await _seed(db_session, "fp-abc", hours_ago=1)
    await _seed(db_session, "fp-abc", hours_ago=2)
    await _seed(db_session, "fp-abc", hours_ago=3)
    result = await get_recurring_fingerprints(db_session)
    assert "fp-abc" in result
    assert result["fp-abc"] == 3


@pytest.mark.asyncio
async def test_recurring_ignores_old_items(db_session: AsyncSession):
    # 3 items but all older than 7 days
    await _seed(db_session, "fp-old", hours_ago=200)
    await _seed(db_session, "fp-old", hours_ago=201)
    await _seed(db_session, "fp-old", hours_ago=202)
    result = await get_recurring_fingerprints(db_session)
    assert "fp-old" not in result


@pytest.mark.asyncio
async def test_is_recurring_true(db_session: AsyncSession):
    for i in range(4):
        await _seed(db_session, "fp-recurring", hours_ago=i + 1)
    assert await is_recurring(db_session, "fp-recurring") is True


@pytest.mark.asyncio
async def test_is_recurring_false(db_session: AsyncSession):
    await _seed(db_session, "fp-once", hours_ago=1)
    assert await is_recurring(db_session, "fp-once") is False


@pytest.mark.asyncio
async def test_is_recurring_empty_fingerprint(db_session: AsyncSession):
    assert await is_recurring(db_session, "") is False


@pytest.mark.asyncio
async def test_triage_list_includes_recurring_flag(client: AsyncClient, db_session: AsyncSession):
    """The /api/triage endpoint includes a recurring flag on items."""
    for i in range(3):
        await _seed(db_session, "fp-repeat", hours_ago=i + 1)
    await _seed(db_session, "fp-single", hours_ago=1)

    resp = await client.get("/api/triage?status=pending")
    assert resp.status_code == 200
    items = resp.json()

    recurring_items = [i for i in items if i["fingerprint"] == "fp-repeat"]
    single_items = [i for i in items if i["fingerprint"] == "fp-single"]

    assert all(i["recurring"] is True for i in recurring_items)
    assert all(i["recurring"] is False for i in single_items)
