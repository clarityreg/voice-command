"""Tests for Plane voice command handlers (create/complete/list tasks)."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.voice.project_resolver import ProjectResolver, ResolveResult


MOCK_PROJECTS = {
    "acme": {"id": "proj-1", "name": "Acme Corp", "identifier": "ACME"},
    "clarity": {"id": "proj-2", "name": "Clarity Regulatory", "identifier": "CLR"},
}


def _mock_resolver():
    return ProjectResolver(MOCK_PROJECTS)


@pytest.mark.asyncio
async def test_create_task_returns_pending_action(client: AsyncClient, db_session: AsyncSession):
    with patch("clarity_backend.voice.commands._get_project_resolver", _mock_resolver):
        resp = await client.post(
            "/api/voice/process",
            json={"text": "create task in acme: fix login bug"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"]["type"] == "plane_create_task"
    pa = data["data"]["pending_action"]
    assert pa["action_type"] == "create_task"
    assert pa["project_id"] == "proj-1"
    assert pa["project_name"] == "Acme Corp"
    assert pa["title"] == "fix login bug"


@pytest.mark.asyncio
async def test_create_task_with_priority(client: AsyncClient, db_session: AsyncSession):
    with patch("clarity_backend.voice.commands._get_project_resolver", _mock_resolver):
        resp = await client.post(
            "/api/voice/process",
            json={"text": "create urgent task in clarity: update docs"},
        )
    data = resp.json()
    pa = data["data"]["pending_action"]
    assert pa["priority"] == "urgent"
    assert pa["project_name"] == "Clarity Regulatory"


@pytest.mark.asyncio
async def test_create_task_unknown_project(client: AsyncClient, db_session: AsyncSession):
    with patch("clarity_backend.voice.commands._get_project_resolver", _mock_resolver):
        resp = await client.post(
            "/api/voice/process",
            json={"text": "create task in nonexistent: do stuff"},
        )
    data = resp.json()
    assert "pending_action" not in data["data"]
    assert "don't know" in data["response"].lower() or "sync" in data["response"].lower()


@pytest.mark.asyncio
async def test_create_task_missing_project(client: AsyncClient, db_session: AsyncSession):
    """If regex can't extract a project name, handler asks which project."""
    resp = await client.post(
        "/api/voice/process",
        json={"text": "create task"},
    )
    # This should hit CREATE_ISSUE or UNKNOWN, not PLANE_CREATE_TASK
    # because the regex requires "in/for <project>"
    data = resp.json()
    assert data["intent"]["type"] != "plane_create_task" or "which project" in data["response"].lower()


@pytest.mark.asyncio
async def test_complete_task_returns_pending_action(client: AsyncClient, db_session: AsyncSession):
    with patch("clarity_backend.voice.commands._get_project_resolver", _mock_resolver):
        resp = await client.post(
            "/api/voice/process",
            json={"text": "complete task ACME-42"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"]["type"] == "plane_complete_task"
    pa = data["data"]["pending_action"]
    assert pa["action_type"] == "complete_task"
    assert pa["project_id"] == "proj-1"
    assert pa["sequence_id"] == 42


@pytest.mark.asyncio
async def test_complete_task_bad_ref(client: AsyncClient, db_session: AsyncSession):
    with patch("clarity_backend.voice.commands._get_project_resolver", _mock_resolver):
        resp = await client.post(
            "/api/voice/process",
            json={"text": "complete task 42"},
        )
    data = resp.json()
    # "42" alone doesn't have a project prefix, so it should fail parsing
    assert "pending_action" not in data["data"]


@pytest.mark.asyncio
async def test_list_tasks_no_project_configured(client: AsyncClient, db_session: AsyncSession):
    """When no projects are synced, should get a helpful message."""
    with (
        patch("clarity_backend.settings.manager.get_plane_projects", return_value={}),
        patch("clarity_backend.settings.manager._read_settings", return_value={
            "plane_api_key": "test-key",
            "plane_workspace_slug": "test-ws",
        }),
    ):
        resp = await client.post(
            "/api/voice/process",
            json={"text": "show my tasks"},
        )
    data = resp.json()
    assert "no projects" in data["response"].lower() or "sync" in data["response"].lower()
