"""Tests for PlaneNotifierService — connection, polling, and config guard."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from clarity_backend.services.plane_notifier import PlaneNotifierService


@pytest.fixture
def configured_settings():
    """Return a mock settings object with Plane credentials set."""
    with patch("clarity_backend.services.plane_notifier.settings") as mock:
        mock.PLANE_API_KEY = "plane-test-key"
        mock.PLANE_API_URL = "https://plane.example.com/api/v1"
        mock.PLANE_WORKSPACE_SLUG = "test-workspace"
        mock.PLANE_PROJECT_ID = "proj-123"
        yield mock


@pytest.fixture
def unconfigured_settings():
    """Return a mock settings object with empty Plane credentials."""
    with patch("clarity_backend.services.plane_notifier.settings") as mock:
        mock.PLANE_API_KEY = ""
        mock.PLANE_API_URL = "https://app.plane.so/api/v1"
        mock.PLANE_WORKSPACE_SLUG = ""
        mock.PLANE_PROJECT_ID = ""
        yield mock


# ---------------------------------------------------------------------------
# _configured property
# ---------------------------------------------------------------------------


def test_configured_when_all_set(configured_settings):
    svc = PlaneNotifierService()
    assert svc._configured is True


def test_not_configured_when_missing_key(unconfigured_settings):
    svc = PlaneNotifierService()
    assert svc._configured is False


# ---------------------------------------------------------------------------
# connect()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_skips_when_unconfigured(unconfigured_settings):
    """connect() returns False immediately when credentials are missing."""
    svc = PlaneNotifierService()
    result = await svc.connect()
    assert result is False


@pytest.mark.asyncio
async def test_connect_success(configured_settings):
    """connect() returns True on successful API call."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch("clarity_backend.services.plane_notifier.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        svc = PlaneNotifierService()
        result = await svc.connect()

    assert result is True
    mock_client.get.assert_awaited_once()
    call_url = mock_client.get.call_args[0][0]
    assert "/workspaces/test-workspace/projects/" in call_url


@pytest.mark.asyncio
async def test_connect_returns_false_on_http_error(configured_settings):
    """connect() returns False when API returns error status."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized", request=MagicMock(), response=MagicMock()
    )

    with patch("clarity_backend.services.plane_notifier.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        svc = PlaneNotifierService()
        result = await svc.connect()

    assert result is False


# ---------------------------------------------------------------------------
# listen() — guard clause
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_listen_returns_immediately_when_unconfigured(unconfigured_settings):
    """listen() should exit immediately without polling when unconfigured."""
    svc = PlaneNotifierService()
    svc._running = True
    # If this enters the while loop it would run forever, so a quick return = pass
    await svc.listen()


# ---------------------------------------------------------------------------
# _issue_to_notification
# ---------------------------------------------------------------------------


def test_issue_to_notification_maps_fields(configured_settings):
    """Converts a Plane issue dict to a Notification."""
    svc = PlaneNotifierService()
    issue = {
        "id": "issue-abc",
        "name": "Fix login bug",
        "priority": "high",
        "description_stripped": "Login fails for OAuth users",
        "updated_at": "2026-03-05T10:00:00Z",
        "state_detail": {"name": "In Progress"},
        "project_detail": {"name": "Backend"},
        "sequence_id": 42,
        "label_detail": [{"name": "bug"}],
    }
    notif = svc._issue_to_notification(issue)
    assert notif.title == "Fix login bug"
    assert notif.source_id == "issue-abc"
    assert notif.project_name == "Backend"


def test_issue_to_notification_handles_missing_fields(configured_settings):
    """Handles issues with minimal/missing optional fields."""
    svc = PlaneNotifierService()
    issue = {"id": "x", "name": "Minimal", "updated_at": "2026-01-01T00:00:00Z"}
    notif = svc._issue_to_notification(issue)
    assert notif.title == "Minimal"


# ---------------------------------------------------------------------------
# create_issue
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_issue_posts_correctly(configured_settings):
    """create_issue() sends correct payload to Plane API."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"id": "new-issue", "name": "Test"}

    with patch("clarity_backend.services.plane_notifier.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        svc = PlaneNotifierService()
        result = await svc.create_issue("Test issue", "A description", "high")

    assert result == {"id": "new-issue", "name": "Test"}
    call_kwargs = mock_client.post.call_args
    assert "Test issue" in str(call_kwargs)


@pytest.mark.asyncio
async def test_create_issue_returns_none_on_error(configured_settings):
    """create_issue() returns None when API call fails."""
    with patch("clarity_backend.services.plane_notifier.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("unreachable"))
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        svc = PlaneNotifierService()
        result = await svc.create_issue("Fail test")

    assert result is None
