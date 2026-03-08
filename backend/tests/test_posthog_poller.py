"""Tests for the PostHog polling service."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from clarity_backend.notifications.models import Priority, Source
from clarity_backend.services.posthog import PostHogPollerService, _normalize_event


@pytest.fixture
def poller():
    with patch.dict(
        "os.environ",
        {
            "DOTENV_CONFIG": "1",
            "POSTHOG_API_KEY": "phx_test_key",
            "POSTHOG_PROJECT_ID": "12345",
            "POSTHOG_HOST": "https://eu.posthog.com",
        },
    ):
        import importlib

        import clarity_backend.config as config_mod

        importlib.reload(config_mod)
        # Re-import so PostHogPollerService picks up the reloaded settings
        import clarity_backend.services.posthog as posthog_mod

        importlib.reload(posthog_mod)
        svc = posthog_mod.PostHogPollerService()
        yield svc


def _make_event(
    exc_type: str = "TypeError",
    exc_message: str = "Cannot read property",
    level: str = "error",
    ts: str = "2026-03-06T12:00:00Z",
) -> dict:
    """Create an event in the events API format (not webhook format)."""
    return {
        "uuid": "evt-001",
        "event": "$exception",
        "timestamp": ts,
        "distinct_id": "user-42",
        "properties": {
            "$exception_list": [
                {"type": exc_type, "value": exc_message, "mechanism": {}, "stacktrace": {}},
            ],
            "$exception_types": [exc_type],
            "$exception_values": [exc_message],
            "$exception_level": level,
            "$current_url": "https://app.example.com/dashboard",
            "$exception_issue_id": "issue-001",
        },
    }


def test_normalize_event():
    raw = _make_event()
    normalized = _normalize_event(raw)
    props = normalized["properties"]
    assert props["$exception_type"] == "TypeError"
    assert props["$exception_message"] == "Cannot read property"
    assert props["$level"] == "error"


def test_normalize_event_already_webhook_format():
    """Events already in webhook format should pass through unchanged."""
    webhook_event = {
        "properties": {"$exception_type": "Foo", "$exception_message": "bar", "$level": "warn"}
    }
    assert _normalize_event(webhook_event) is webhook_event


def test_event_to_notification(poller):
    event = _normalize_event(_make_event())
    notification = poller._event_to_notification(event)

    assert notification.source == Source.POSTHOG
    assert notification.source_account == "PostHog"
    assert notification.source_id == "evt-001"
    assert notification.title == "TypeError"
    assert "Cannot read property" in notification.body
    assert "URL: https://app.example.com/dashboard" in notification.body
    assert "User: user-42" in notification.body
    assert notification.priority == Priority.HIGH
    assert notification.raw_payload["distinct_id"] == "user-42"
    assert notification.raw_payload["exception_type"] == "TypeError"
    assert notification.raw_payload["exception_message"] == "Cannot read property"


def test_event_to_notification_critical(poller):
    event = _normalize_event(_make_event(exc_message="fatal crash OOM", level="critical"))
    notification = poller._event_to_notification(event)
    assert notification.priority == Priority.URGENT


def test_event_to_notification_low(poller):
    event = _normalize_event(_make_event(level="info"))
    notification = poller._event_to_notification(event)
    assert notification.priority == Priority.LOW


def test_event_to_notification_bad_timestamp(poller):
    event = _normalize_event(_make_event(ts="not-a-date"))
    notification = poller._event_to_notification(event)
    assert notification.timestamp is not None


def test_not_configured_without_api_key():
    with patch.dict(
        "os.environ",
        {"DOTENV_CONFIG": "1", "POSTHOG_API_KEY": "", "POSTHOG_PROJECT_ID": ""},
    ):
        import importlib

        import clarity_backend.config as config_mod
        import clarity_backend.services.posthog as posthog_mod

        importlib.reload(config_mod)
        importlib.reload(posthog_mod)
        svc = posthog_mod.PostHogPollerService()
        assert not svc._configured


async def test_fetch_recent_returns_notifications(poller):
    mock_events = [_make_event(), _make_event(exc_type="ReferenceError")]
    with patch.object(poller, "_fetch_events", new_callable=AsyncMock, return_value=mock_events):
        # Ensure _configured returns True for this test
        with patch.object(type(poller), "_configured", new_callable=lambda: property(lambda self: True)):
            notifications = await poller.fetch_recent(limit=10)
    assert len(notifications) == 2
    assert notifications[0].source == Source.POSTHOG


async def test_fetch_events_calls_api(poller):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": [_make_event()]}
    mock_response.raise_for_status.return_value = None

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    mock_client.get.return_value = mock_response

    with patch("clarity_backend.services.posthog.httpx.AsyncClient", return_value=mock_client):
        events = await poller._fetch_events(limit=10)

    assert len(events) == 1
    mock_client.get.assert_called_once()
    call_url = mock_client.get.call_args[0][0]
    assert "/api/projects/12345/events/" in call_url
