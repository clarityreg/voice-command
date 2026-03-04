"""Tests for the error investigation module."""

import json
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.models import TriageItem
from clarity_backend.triage.investigator import (
    _fallback_result,
    _parse_investigation,
    investigate,
)


def test_fallback_result():
    result = _fallback_result("Test error", "Some desc", "high", "posthog")
    assert "manual review" in result["root_cause"].lower() or "unavailable" in result["root_cause"].lower()
    assert result["affected_files"] == []
    assert "Test error" in result["suggested_fix"]
    assert result["raw_response"] != ""


def test_parse_investigation_structured():
    text = """ROOT CAUSE: The database connection pool is exhausted due to leaked connections.
AFFECTED FILES: src/db/pool.py, src/api/handler.py
SUGGESTED FIX: Add connection pool cleanup in the finally block."""
    result = _parse_investigation(text, "DB pool error")
    assert "exhausted" in result["root_cause"]
    assert "src/db/pool.py" in result["affected_files"]
    assert "src/api/handler.py" in result["affected_files"]
    assert "cleanup" in result["suggested_fix"]
    assert result["raw_response"] == text


def test_parse_investigation_unknown_files():
    text = """ROOT CAUSE: Something broke.
AFFECTED FILES: Unknown
SUGGESTED FIX: Check the logs."""
    result = _parse_investigation(text, "Error")
    assert result["affected_files"] == []


def test_parse_investigation_multiline():
    text = """ROOT CAUSE: The error occurs because the middleware
is not properly handling async exceptions.
AFFECTED FILES: src/middleware.py
SUGGESTED FIX: Wrap the handler in a try/except
and propagate the error correctly."""
    result = _parse_investigation(text, "Middleware error")
    assert "middleware" in result["root_cause"].lower()
    assert "async" in result["root_cause"]
    assert "src/middleware.py" in result["affected_files"]
    assert "try/except" in result["suggested_fix"]


@pytest.mark.asyncio
async def test_investigate_fallback_no_claude(monkeypatch):
    """When Claude CLI is not found, should return fallback result."""
    monkeypatch.setattr("clarity_backend.triage.investigator._CLAUDE_PATH", None)
    result = await investigate("Test error", "Description", "critical", "posthog", {})
    assert "unavailable" in result["root_cause"].lower() or "manual" in result["root_cause"].lower()
    assert result["affected_files"] == []


async def _seed_item(session: AsyncSession) -> TriageItem:
    item = TriageItem(
        source="posthog",
        title="Test Error",
        description="Something went wrong",
        severity="high",
        status="pending",
        fingerprint="fp-inv-001",
        occurrence_count=1,
        first_seen=datetime.now(UTC),
        last_seen=datetime.now(UTC),
        metadata_json="{}",
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@pytest.mark.asyncio
async def test_investigate_endpoint(client: AsyncClient, db_session: AsyncSession, monkeypatch):
    """The /investigate endpoint should return investigation results."""
    monkeypatch.setattr("clarity_backend.triage.investigator._CLAUDE_PATH", None)
    item = await _seed_item(db_session)
    resp = await client.post(f"/api/triage/{item.id}/investigate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["item_id"] == item.id
    assert "root_cause" in data["investigation"]
    assert "suggested_fix" in data["investigation"]
    assert "affected_files" in data["investigation"]


@pytest.mark.asyncio
async def test_investigate_endpoint_not_found(client: AsyncClient):
    resp = await client.post("/api/triage/99999/investigate")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_investigate_stores_in_metadata(client: AsyncClient, db_session: AsyncSession, monkeypatch):
    """Investigation result should be stored in the item's metadata."""
    monkeypatch.setattr("clarity_backend.triage.investigator._CLAUDE_PATH", None)
    item = await _seed_item(db_session)
    await client.post(f"/api/triage/{item.id}/investigate")
    await db_session.refresh(item)
    metadata = json.loads(item.metadata_json)
    assert "investigation" in metadata
    assert "root_cause" in metadata["investigation"]
