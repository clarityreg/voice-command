"""Tests for voice command execution via the API endpoint."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.models import TriageItem


async def _seed_item(
    session: AsyncSession,
    source: str = "posthog",
    severity: str = "high",
    status: str = "pending",
    hours_ago: int = 1,
) -> TriageItem:
    now = datetime.now(UTC).replace(tzinfo=None)
    item = TriageItem(
        source=source,
        title=f"Test {source} item",
        description="test",
        severity=severity,
        status=status,
        fingerprint=f"fp-{source}-{now.timestamp()}",
        first_seen=now - timedelta(hours=hours_ago),
        last_seen=now,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@pytest.mark.asyncio
async def test_process_query_errors(client: AsyncClient, db_session: AsyncSession):
    await _seed_item(db_session, source="posthog", severity="critical")
    await _seed_item(db_session, source="posthog", severity="high")

    resp = await client.post("/api/voice/process", json={"text": "What errors came in today?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"]["type"] == "query_errors"
    assert "2 errors" in data["response"]


@pytest.mark.asyncio
async def test_process_query_vulns(client: AsyncClient, db_session: AsyncSession):
    await _seed_item(db_session, source="aikido")

    resp = await client.post("/api/voice/process", json={"text": "Any new vulnerabilities?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"]["type"] == "query_vulns"
    assert "1 vulnerability" in data["response"]


@pytest.mark.asyncio
async def test_process_status(client: AsyncClient, db_session: AsyncSession):
    await _seed_item(db_session, severity="critical")
    await _seed_item(db_session, severity="low")

    resp = await client.post("/api/voice/process", json={"text": "What's my status?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"]["type"] == "check_status"
    assert "2 items pending" in data["response"]
    assert "1 critical" in data["response"]


@pytest.mark.asyncio
async def test_process_morning_brief_empty(client: AsyncClient):
    resp = await client.post("/api/voice/process", json={"text": "Give me the morning brief"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"]["type"] == "morning_brief"
    assert "0 new errors" in data["response"]


@pytest.mark.asyncio
async def test_process_create_issue_with_id(client: AsyncClient):
    resp = await client.post("/api/voice/process", json={"text": "Create an issue for item #42"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"]["type"] == "create_issue"
    assert data["data"]["item_id"] == 42


@pytest.mark.asyncio
async def test_process_snooze_without_id(client: AsyncClient):
    resp = await client.post("/api/voice/process", json={"text": "Snooze this"})
    assert resp.status_code == 200
    data = resp.json()
    assert "Which item" in data["response"]


@pytest.mark.asyncio
async def test_process_unknown(client: AsyncClient):
    resp = await client.post("/api/voice/process", json={"text": "Tell me a joke"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"]["type"] == "unknown"
    assert "didn't understand" in data["response"]


@pytest.mark.asyncio
async def test_process_empty_text(client: AsyncClient):
    resp = await client.post("/api/voice/process", json={"text": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"]["type"] == "unknown"
