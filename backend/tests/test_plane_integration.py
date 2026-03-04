"""Tests for Plane API integration."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import Response

from clarity_backend.integrations.plane import PlaneClient, severity_to_priority
from clarity_backend.models import TriageItem


# ---------------------------------------------------------------------------
# severity_to_priority
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "severity, expected",
    [
        ("critical", "urgent"),
        ("high", "high"),
        ("medium", "medium"),
        ("low", "low"),
        ("unknown", "low"),
    ],
)
def test_severity_to_priority(severity: str, expected: str) -> None:
    assert severity_to_priority(severity) == expected


# ---------------------------------------------------------------------------
# PlaneClient.create_work_item
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plane_client_create_work_item() -> None:
    mock_response_data = {"id": "issue-123", "name": "[PostHog] Error spike", "url": "https://example.com/issue-123"}

    mock_response = MagicMock(spec=Response)
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status = MagicMock()

    with patch("clarity_backend.integrations.plane.httpx.AsyncClient") as mock_client_cls:
        mock_async_client = AsyncMock()
        mock_async_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        client = PlaneClient(
            api_key="test-key",
            workspace_slug="my-workspace",
            project_id="proj-abc",
        )
        result = await client.create_work_item(
            title="[PostHog] Error spike",
            description_html="<p>Some error</p>",
            priority="urgent",
            labels=["bug", "posthog-auto"],
        )

    assert result == mock_response_data
    mock_async_client.post.assert_called_once_with(
        "https://plane-api.clarityregulatory.work/api/v1/workspaces/my-workspace/projects/proj-abc/issues/",
        headers={"X-API-Key": "test-key", "Content-Type": "application/json"},
        json={
            "name": "[PostHog] Error spike",
            "description_html": "<p>Some error</p>",
            "priority": "urgent",
            "labels": ["bug", "posthog-auto"],
        },
    )


# ---------------------------------------------------------------------------
# POST /api/triage/{item_id}/create-issue endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_issue_endpoint(client) -> None:
    # Insert a triage item
    from sqlmodel import select
    from clarity_backend.database import get_session
    from clarity_backend.main import app

    # Get session from app dependency overrides (set up by conftest)
    session = None
    async for s in app.dependency_overrides[get_session]():
        session = s

    item = TriageItem(
        source="posthog",
        title="NullPointerException",
        description="Error in auth flow",
        severity="high",
        metadata_json="{}",
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    item_id = item.id

    mock_issue = {"id": "plane-issue-1", "url": "https://plane.example.com/issue-1"}

    with patch("clarity_backend.integrations.routes.PlaneClient") as MockPlane:
        mock_instance = AsyncMock()
        mock_instance.create_work_item = AsyncMock(return_value=mock_issue)
        MockPlane.return_value = mock_instance

        response = await client.post(f"/api/triage/{item_id}/create-issue")

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "plane-issue-1"

    # Verify triage item was updated
    result = await session.exec(select(TriageItem).where(TriageItem.id == item_id))
    updated = result.first()
    assert updated.status == "actioned"
    metadata = json.loads(updated.metadata_json)
    assert metadata["plane_issue_id"] == "plane-issue-1"


@pytest.mark.asyncio
async def test_create_issue_endpoint_aikido_prefix(client) -> None:
    from clarity_backend.database import get_session
    from clarity_backend.main import app

    session = None
    async for s in app.dependency_overrides[get_session]():
        session = s

    item = TriageItem(
        source="aikido",
        title="SQL injection risk",
        description="Detected in user query",
        severity="critical",
        metadata_json="{}",
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    item_id = item.id

    mock_issue = {"id": "plane-issue-2", "url": "https://plane.example.com/issue-2"}

    with patch("clarity_backend.integrations.routes.PlaneClient") as MockPlane:
        mock_instance = AsyncMock()
        mock_instance.create_work_item = AsyncMock(return_value=mock_issue)
        MockPlane.return_value = mock_instance

        response = await client.post(f"/api/triage/{item_id}/create-issue")
        call_kwargs = mock_instance.create_work_item.call_args

    assert response.status_code == 201
    assert call_kwargs.kwargs["title"].startswith("[Aikido]")
    assert call_kwargs.kwargs["priority"] == "urgent"
    assert "aikido-auto" in call_kwargs.kwargs["labels"]


@pytest.mark.asyncio
async def test_create_issue_endpoint_not_found(client) -> None:
    response = await client.post("/api/triage/99999/create-issue")
    assert response.status_code == 404
    assert response.json()["detail"] == "Triage item not found"
