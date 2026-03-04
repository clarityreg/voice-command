"""Tests for GET /api/brief/morning endpoint."""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.models import TriageItem


async def _seed(session: AsyncSession, **overrides) -> TriageItem:
    defaults = {
        "source": "posthog",
        "title": "Test",
        "severity": "high",
        "status": "pending",
        "fingerprint": "fp-brief",
    }
    defaults.update(overrides)
    item = TriageItem(**defaults)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@pytest.mark.asyncio
async def test_morning_brief_empty_db(client: AsyncClient):
    """Returns all zeros on empty database."""
    resp = await client.get("/api/brief/morning")
    assert resp.status_code == 200
    data = resp.json()
    assert data["new_errors_24h"] == 0
    assert data["new_vulns_24h"] == 0
    assert data["actioned_yesterday"] == 0
    assert data["pending_total"] == 0
    assert data["top_severity"] is None


@pytest.mark.asyncio
async def test_morning_brief_counts_errors(client: AsyncClient, db_session: AsyncSession):
    """Counts posthog items created in last 24h as new errors."""
    await _seed(db_session, source="posthog", fingerprint="fp-e1")
    await _seed(db_session, source="posthog", fingerprint="fp-e2")
    resp = await client.get("/api/brief/morning")
    assert resp.json()["new_errors_24h"] == 2


@pytest.mark.asyncio
async def test_morning_brief_counts_vulns(client: AsyncClient, db_session: AsyncSession):
    """Counts aikido items created in last 24h as new vulns."""
    await _seed(db_session, source="aikido", fingerprint="fp-v1")
    resp = await client.get("/api/brief/morning")
    assert resp.json()["new_vulns_24h"] == 1


@pytest.mark.asyncio
async def test_morning_brief_pending_total(client: AsyncClient, db_session: AsyncSession):
    """Counts all pending items regardless of time."""
    await _seed(db_session, status="pending", fingerprint="fp-p1")
    await _seed(db_session, status="snoozed", fingerprint="fp-p2")
    resp = await client.get("/api/brief/morning")
    assert resp.json()["pending_total"] == 1


@pytest.mark.asyncio
async def test_morning_brief_top_severity(client: AsyncClient, db_session: AsyncSession):
    """Returns highest severity among pending items."""
    await _seed(db_session, severity="medium", status="pending", fingerprint="fp-s1")
    await _seed(db_session, severity="critical", status="pending", fingerprint="fp-s2")
    resp = await client.get("/api/brief/morning")
    assert resp.json()["top_severity"] == "critical"
