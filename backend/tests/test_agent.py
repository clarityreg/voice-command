"""Tests for agent job routes."""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession
from unittest.mock import patch, AsyncMock

from clarity_backend.models import TriageItem


async def _seed_triage_item(session: AsyncSession, **overrides) -> TriageItem:
    """Helper to insert a triage item with sensible defaults."""
    defaults = {
        "source": "posthog",
        "title": "Test Error",
        "description": "A test error",
        "severity": "high",
        "status": "pending",
        "fingerprint": "fp-agent-test",
        "occurrence_count": 1,
    }
    defaults.update(overrides)
    item = TriageItem(**defaults)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


# --- POST /api/agent/fix/{item_id} ---

@pytest.mark.asyncio
async def test_start_fix_returns_job_id(client: AsyncClient, db_session: AsyncSession):
    """POST /api/agent/fix/{id} creates a job and returns job_id."""
    item = await _seed_triage_item(db_session)
    with patch("clarity_backend.agent.routes.create_plan", new_callable=AsyncMock):
        resp = await client.post(f"/api/agent/fix/{item.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "planning"


@pytest.mark.asyncio
async def test_start_fix_not_found(client: AsyncClient):
    """POST /api/agent/fix/999 returns 404 for non-existent item."""
    resp = await client.post("/api/agent/fix/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_start_fix_no_claude_cli(client: AsyncClient, db_session: AsyncSession):
    """Fix endpoint succeeds even when Claude CLI is not in PATH."""
    item = await _seed_triage_item(db_session, fingerprint="fp-no-cli")
    with patch("shutil.which", return_value=None), \
         patch("clarity_backend.agent.routes.create_plan", new_callable=AsyncMock):
        resp = await client.post(f"/api/agent/fix/{item.id}")
    assert resp.status_code == 200
    assert "job_id" in resp.json()


# --- GET /api/agent/jobs ---

@pytest.mark.asyncio
async def test_list_jobs_empty(client: AsyncClient):
    """GET /api/agent/jobs returns empty list when no jobs exist."""
    resp = await client.get("/api/agent/jobs")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_jobs_returns_created(client: AsyncClient, db_session: AsyncSession):
    """GET /api/agent/jobs returns the created job."""
    item = await _seed_triage_item(db_session, fingerprint="fp-list-test")
    with patch("clarity_backend.agent.routes.create_plan", new_callable=AsyncMock):
        await client.post(f"/api/agent/fix/{item.id}")

    resp = await client.get("/api/agent/jobs")
    assert resp.status_code == 200
    jobs = resp.json()
    assert len(jobs) == 1
    assert jobs[0]["triage_item_id"] == item.id


# --- GET /api/agent/jobs/{job_id} ---

@pytest.mark.asyncio
async def test_get_job_returns_single(client: AsyncClient, db_session: AsyncSession):
    """GET /api/agent/jobs/{id} returns the job by ID."""
    item = await _seed_triage_item(db_session, fingerprint="fp-get-test")
    with patch("clarity_backend.agent.routes.create_plan", new_callable=AsyncMock):
        fix_resp = await client.post(f"/api/agent/fix/{item.id}")
    job_id = fix_resp.json()["job_id"]

    resp = await client.get(f"/api/agent/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id


# --- POST /api/agent/jobs/{job_id}/approve ---

@pytest.mark.asyncio
async def test_approve_job_wrong_status_returns_400(client: AsyncClient, db_session: AsyncSession):
    """POST /api/agent/jobs/{id}/approve returns 400 when status is not plan_ready."""
    item = await _seed_triage_item(db_session, fingerprint="fp-approve-test")
    with patch("clarity_backend.agent.routes.create_plan", new_callable=AsyncMock):
        fix_resp = await client.post(f"/api/agent/fix/{item.id}")
    job_id = fix_resp.json()["job_id"]

    # Job is in 'planning' state, not 'plan_ready'
    resp = await client.post(f"/api/agent/jobs/{job_id}/approve")
    assert resp.status_code == 400


# --- POST /api/agent/jobs/{job_id}/cancel ---

@pytest.mark.asyncio
async def test_cancel_job(client: AsyncClient, db_session: AsyncSession):
    """POST /api/agent/jobs/{id}/cancel transitions the job to cancelled."""
    item = await _seed_triage_item(db_session, fingerprint="fp-cancel-test")
    with patch("clarity_backend.agent.routes.create_plan", new_callable=AsyncMock):
        fix_resp = await client.post(f"/api/agent/fix/{item.id}")
    job_id = fix_resp.json()["job_id"]

    resp = await client.post(f"/api/agent/jobs/{job_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
