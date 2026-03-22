"""Tests for AsanaService — connection, polling, task mapping, and error handling."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from clarity_backend.notifications.models import NotificationType, Priority, Source
from clarity_backend.services.asana import AsanaService


@pytest.fixture
def configured_settings():
    """Return a mock settings object with Asana credentials set."""
    with patch("clarity_backend.services.asana.settings") as mock:
        mock.ASANA_ACCESS_TOKEN = "asana-test-token"
        mock.ASANA_DEFAULT_WORKSPACE_GID = "workspace-123"
        mock.ASANA_DEFAULT_PROJECT_GID = "project-456"
        yield mock


_SENTINEL = object()


def _make_task(
    gid: str = "task-001",
    name: str = "Fix the bug",
    notes: str = "Details here",
    due_on: str | None = None,
    completed: bool = False,
    projects: list | None = _SENTINEL,  # type: ignore[assignment]
    modified_at: str = "2026-03-05T12:00:00Z",
) -> dict:
    if projects is _SENTINEL:
        projects = [{"name": "Backend"}]
    return {
        "gid": gid,
        "name": name,
        "notes": notes,
        "due_on": due_on,
        "completed": completed,
        "projects": projects,
        "modified_at": modified_at,
    }


def _make_async_client(json_data: dict | None = None, raise_error: Exception | None = None):
    """Build a mocked httpx.AsyncClient context manager."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    if json_data is not None:
        mock_response.json.return_value = json_data

    mock_client = AsyncMock()
    if raise_error:
        mock_client.get = AsyncMock(side_effect=raise_error)
        mock_client.post = AsyncMock(side_effect=raise_error)
    else:
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client, mock_response


# ---------------------------------------------------------------------------
# connect()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_success(configured_settings):
    """connect() returns True when /users/me succeeds."""
    mock_client, mock_response = _make_async_client(
        json_data={"data": {"name": "Test User", "gid": "user-1"}}
    )
    with patch("clarity_backend.services.asana.httpx.AsyncClient", return_value=mock_client):
        svc = AsanaService()
        result = await svc.connect()

    assert result is True
    mock_client.get.assert_awaited_once()
    call_url = mock_client.get.call_args[0][0]
    assert "/users/me" in call_url


@pytest.mark.asyncio
async def test_connect_returns_false_on_http_error(configured_settings):
    """connect() returns False when the API responds with an error status."""
    mock_client, mock_response = _make_async_client()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized", request=MagicMock(), response=MagicMock()
    )
    with patch("clarity_backend.services.asana.httpx.AsyncClient", return_value=mock_client):
        svc = AsanaService()
        result = await svc.connect()

    assert result is False


@pytest.mark.asyncio
async def test_connect_returns_false_on_network_error(configured_settings):
    """connect() returns False when a network-level error occurs."""
    mock_client, _ = _make_async_client(raise_error=httpx.ConnectError("unreachable"))
    with patch("clarity_backend.services.asana.httpx.AsyncClient", return_value=mock_client):
        svc = AsanaService()
        result = await svc.connect()

    assert result is False


# ---------------------------------------------------------------------------
# disconnect()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disconnect_is_noop(configured_settings):
    """disconnect() completes without error (Asana has no persistent connection)."""
    svc = AsanaService()
    await svc.disconnect()  # should not raise


# ---------------------------------------------------------------------------
# fetch_recent()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_recent_returns_notifications(configured_settings):
    """fetch_recent() converts API tasks into Notification objects."""
    tasks = [_make_task(), _make_task(gid="task-002", name="Second task")]
    mock_client, _ = _make_async_client(json_data={"data": tasks})

    with patch("clarity_backend.services.asana.httpx.AsyncClient", return_value=mock_client):
        svc = AsanaService()
        result = await svc.fetch_recent(limit=10)

    assert len(result) == 2
    assert result[0].source == Source.ASANA
    assert result[0].title == "Fix the bug"
    assert result[1].source_id == "task-002"


@pytest.mark.asyncio
async def test_fetch_recent_passes_correct_params(configured_settings):
    """fetch_recent() sends workspace GID and limit to the API."""
    mock_client, _ = _make_async_client(json_data={"data": []})

    with patch("clarity_backend.services.asana.httpx.AsyncClient", return_value=mock_client):
        svc = AsanaService()
        await svc.fetch_recent(limit=5)

    call_kwargs = mock_client.get.call_args
    params = call_kwargs[1]["params"]
    assert params["limit"] == 5
    assert params["workspace"] == "workspace-123"
    assert params["assignee"] == "me"


@pytest.mark.asyncio
async def test_fetch_recent_returns_empty_on_error(configured_settings):
    """fetch_recent() returns an empty list when the API fails."""
    mock_client, _ = _make_async_client(raise_error=httpx.ConnectError("down"))

    with patch("clarity_backend.services.asana.httpx.AsyncClient", return_value=mock_client):
        svc = AsanaService()
        result = await svc.fetch_recent()

    assert result == []


# ---------------------------------------------------------------------------
# listen()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_listen_polls_and_emits(configured_settings):
    """listen() calls emit_notification for each returned task (one iteration)."""
    tasks = [_make_task()]
    mock_client, _ = _make_async_client(json_data={"data": tasks})

    with patch("clarity_backend.services.asana.httpx.AsyncClient", return_value=mock_client):
        with patch("clarity_backend.services.asana.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            svc = AsanaService()
            svc._running = True

            async def stop_after_first(*_):
                svc._running = False

            mock_sleep.side_effect = stop_after_first

            with patch.object(svc, "emit_notification", new_callable=AsyncMock) as mock_emit:
                await svc.listen()

    mock_emit.assert_awaited_once()
    emitted = mock_emit.call_args[0][0]
    assert emitted.source == Source.ASANA
    assert emitted.source_id == "task-001"


@pytest.mark.asyncio
async def test_listen_handles_poll_error_gracefully(configured_settings):
    """listen() does not crash when the API returns an error; it sleeps and tries again."""
    mock_client, _ = _make_async_client(raise_error=httpx.ConnectError("down"))

    with patch("clarity_backend.services.asana.httpx.AsyncClient", return_value=mock_client):
        with patch("clarity_backend.services.asana.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            svc = AsanaService()
            svc._running = True

            async def stop_after_first(*_):
                svc._running = False

            mock_sleep.side_effect = stop_after_first
            await svc.listen()  # should not raise


# ---------------------------------------------------------------------------
# create_task()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_task_posts_correctly(configured_settings):
    """create_task() sends title, notes, and project to the Asana API."""
    created = {"gid": "new-task", "name": "New Task"}
    mock_client, _ = _make_async_client(json_data={"data": created})

    with patch("clarity_backend.services.asana.httpx.AsyncClient", return_value=mock_client):
        svc = AsanaService()
        result = await svc.create_task("New Task", "Some description")

    assert result == created
    call_kwargs = mock_client.post.call_args
    payload = call_kwargs[1]["json"]["data"]
    assert payload["name"] == "New Task"
    assert payload["notes"] == "Some description"
    assert "project-456" in payload["projects"]


@pytest.mark.asyncio
async def test_create_task_uses_provided_project_gid(configured_settings):
    """create_task() uses the explicitly-passed project_gid over the default."""
    mock_client, _ = _make_async_client(json_data={"data": {"gid": "t", "name": "T"}})

    with patch("clarity_backend.services.asana.httpx.AsyncClient", return_value=mock_client):
        svc = AsanaService()
        await svc.create_task("T", project_gid="custom-project-gid")

    payload = mock_client.post.call_args[1]["json"]["data"]
    assert "custom-project-gid" in payload["projects"]


@pytest.mark.asyncio
async def test_create_task_returns_none_on_error(configured_settings):
    """create_task() returns None when the API call fails."""
    mock_client, _ = _make_async_client(raise_error=httpx.ConnectError("down"))

    with patch("clarity_backend.services.asana.httpx.AsyncClient", return_value=mock_client):
        svc = AsanaService()
        result = await svc.create_task("Fail task")

    assert result is None


# ---------------------------------------------------------------------------
# _task_to_notification()
# ---------------------------------------------------------------------------


def test_task_to_notification_maps_fields(configured_settings):
    """_task_to_notification maps all standard fields correctly."""
    svc = AsanaService()
    task = _make_task(
        gid="task-abc",
        name="Deploy service",
        notes="Deploy to production",
        projects=[{"name": "Infra"}],
    )
    notif = svc._task_to_notification(task)

    assert notif.source == Source.ASANA
    assert notif.source_account == "Asana"
    assert notif.source_id == "task-abc"
    assert notif.title == "Deploy service"
    assert notif.body == "Deploy to production"
    assert notif.project_name == "Infra"
    assert notif.notification_type == NotificationType.TASK_UPDATE
    assert notif.priority == Priority.NORMAL


def test_task_to_notification_no_project(configured_settings):
    """_task_to_notification defaults project_name to 'No Project' when absent."""
    svc = AsanaService()
    task = _make_task(projects=[])
    notif = svc._task_to_notification(task)
    assert notif.project_name == "No Project"


def test_task_to_notification_overdue_is_urgent(configured_settings):
    """_task_to_notification sets URGENT priority for overdue tasks."""
    svc = AsanaService()
    task = _make_task(due_on="2020-01-01")
    notif = svc._task_to_notification(task)
    assert notif.priority == Priority.URGENT


def test_task_to_notification_due_soon_is_high(configured_settings):
    """_task_to_notification sets HIGH priority for tasks due within 2 days."""
    from datetime import timedelta

    tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
    svc = AsanaService()
    task = _make_task(due_on=tomorrow)
    notif = svc._task_to_notification(task)
    assert notif.priority == Priority.HIGH


def test_task_to_notification_body_truncated(configured_settings):
    """_task_to_notification truncates notes to 300 characters."""
    svc = AsanaService()
    task = _make_task(notes="x" * 500)
    notif = svc._task_to_notification(task)
    assert len(notif.body) <= 300


def test_task_to_notification_raw_payload(configured_settings):
    """_task_to_notification stores due_on and completed in raw_payload."""
    svc = AsanaService()
    task = _make_task(due_on="2026-12-31", completed=False)
    notif = svc._task_to_notification(task)
    assert notif.raw_payload["due_on"] == "2026-12-31"
    assert notif.raw_payload["completed"] is False
