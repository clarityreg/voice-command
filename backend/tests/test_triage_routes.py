"""Tests for triage CRUD routes and status endpoint."""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.models import TriageItem


async def _seed_item(session: AsyncSession, **overrides) -> TriageItem:
    """Helper to insert a triage item with sensible defaults."""
    defaults = {
        "source": "posthog",
        "title": "Test Error",
        "description": "A test error",
        "severity": "high",
        "status": "pending",
        "fingerprint": "fp-test",
        "occurrence_count": 1,
    }
    defaults.update(overrides)
    item = TriageItem(**defaults)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


# --- GET /api/triage ---

@pytest.mark.asyncio
async def test_list_triage_items_empty(client: AsyncClient):
    """Returns empty list when no items exist."""
    resp = await client.get("/api/triage")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_triage_items_returns_seeded(client: AsyncClient, db_session: AsyncSession):
    """Returns seeded items with correct fields."""
    await _seed_item(db_session, title="Error A", fingerprint="fp-a")
    resp = await client.get("/api/triage")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Error A"
    assert data[0]["source"] == "posthog"
    assert data[0]["severity"] == "high"


@pytest.mark.asyncio
async def test_list_triage_items_filter_by_status(client: AsyncClient, db_session: AsyncSession):
    """Status filter returns only matching items."""
    await _seed_item(db_session, title="Pending", fingerprint="fp-p", status="pending")
    await _seed_item(db_session, title="Snoozed", fingerprint="fp-s", status="snoozed")
    resp = await client.get("/api/triage?status=snoozed")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Snoozed"


@pytest.mark.asyncio
async def test_list_triage_items_filter_by_source(client: AsyncClient, db_session: AsyncSession):
    """Source filter returns only matching items."""
    await _seed_item(db_session, title="PostHog", fingerprint="fp-ph", source="posthog")
    await _seed_item(db_session, title="Aikido", fingerprint="fp-ak", source="aikido")
    resp = await client.get("/api/triage?source=aikido")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Aikido"


@pytest.mark.asyncio
async def test_list_triage_items_pagination(client: AsyncClient, db_session: AsyncSession):
    """Limit and offset control pagination."""
    for i in range(5):
        await _seed_item(db_session, title=f"Item {i}", fingerprint=f"fp-{i}")
    resp = await client.get("/api/triage?limit=2&offset=0")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# --- POST /api/triage/{id}/snooze ---

@pytest.mark.asyncio
async def test_snooze_item(client: AsyncClient, db_session: AsyncSession):
    """Snoozing changes status to snoozed."""
    item = await _seed_item(db_session)
    resp = await client.post(f"/api/triage/{item.id}/snooze")
    assert resp.status_code == 200
    assert resp.json()["status"] == "snoozed"


@pytest.mark.asyncio
async def test_snooze_item_not_found(client: AsyncClient):
    """Snoozing a non-existent item returns 404."""
    resp = await client.post("/api/triage/9999/snooze")
    assert resp.status_code == 404


# --- POST /api/triage/{id}/dismiss ---

@pytest.mark.asyncio
async def test_dismiss_item(client: AsyncClient, db_session: AsyncSession):
    """Dismissing changes status and stores reason in metadata."""
    item = await _seed_item(db_session)
    resp = await client.post(
        f"/api/triage/{item.id}/dismiss",
        json={"reason": "not relevant"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "dismissed"
    assert data["metadata"]["dismiss_reason"] == "not relevant"
    assert "dismissed_at" in data["metadata"]


@pytest.mark.asyncio
async def test_dismiss_item_not_found(client: AsyncClient):
    """Dismissing a non-existent item returns 404."""
    resp = await client.post("/api/triage/9999/dismiss", json={"reason": ""})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_dismiss_item_empty_reason(client: AsyncClient, db_session: AsyncSession):
    """Dismissing with empty reason still works."""
    item = await _seed_item(db_session)
    resp = await client.post(
        f"/api/triage/{item.id}/dismiss",
        json={"reason": ""},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "dismissed"


# --- GET /api/status ---

@pytest.mark.asyncio
async def test_status_empty_db(client: AsyncClient):
    """Status returns zeros when no items exist."""
    resp = await client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["critical_count"] == 0
    assert data["vulnerability_count"] == 0
    assert data["actioned_today"] == 0
    assert data["pending_count"] == 0


@pytest.mark.asyncio
async def test_status_counts_critical_pending(client: AsyncClient, db_session: AsyncSession):
    """Status correctly counts critical pending items."""
    await _seed_item(db_session, severity="critical", status="pending", fingerprint="fp-c1")
    await _seed_item(db_session, severity="critical", status="snoozed", fingerprint="fp-c2")
    await _seed_item(db_session, severity="high", status="pending", fingerprint="fp-h1")
    resp = await client.get("/api/status")
    data = resp.json()
    assert data["critical_count"] == 1  # only pending critical
    assert data["pending_count"] == 2  # critical + high pending


@pytest.mark.asyncio
async def test_status_counts_vulnerabilities(client: AsyncClient, db_session: AsyncSession):
    """Status correctly counts aikido pending items as vulnerabilities."""
    await _seed_item(db_session, source="aikido", status="pending", fingerprint="fp-v1")
    await _seed_item(db_session, source="aikido", status="dismissed", fingerprint="fp-v2")
    await _seed_item(db_session, source="posthog", status="pending", fingerprint="fp-p1")
    resp = await client.get("/api/status")
    data = resp.json()
    assert data["vulnerability_count"] == 1  # only pending aikido
