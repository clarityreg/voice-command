"""Tests for SlackService — connection, message fetching, mapping, and error handling."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from clarity_backend.notifications.models import NotificationType, Priority, Source
from clarity_backend.services.slack import SlackService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(
    workspace: str = "test-workspace",
    bot_token: str = "xoxb-test",
    app_token: str = "xapp-test",
) -> SlackService:
    return SlackService(workspace, bot_token, app_token)


def _make_message(
    user: str = "U001",
    text: str = "Hello team",
    ts: str = "1741000000.000100",
    thread_ts: str | None = None,
    subtype: str | None = None,
) -> dict:
    msg: dict = {"user": user, "text": text, "ts": ts}
    if thread_ts is not None:
        msg["thread_ts"] = thread_ts
    if subtype is not None:
        msg["subtype"] = subtype
    return msg


# ---------------------------------------------------------------------------
# connect()
# ---------------------------------------------------------------------------


async def test_connect_success():
    """connect() returns True when auth_test() responds with ok=True."""
    svc = _make_service()

    mock_web_client = AsyncMock()
    mock_web_client.auth_test = AsyncMock(return_value={"ok": True})

    mock_socket_client = MagicMock()

    with patch(
        "clarity_backend.services.slack.AsyncWebClient", return_value=mock_web_client
    ):
        with patch(
            "clarity_backend.services.slack.SocketModeClient",
            return_value=mock_socket_client,
        ):
            result = await svc.connect()

    assert result is True
    assert svc._web_client is mock_web_client
    assert svc._socket_client is mock_socket_client


async def test_connect_returns_false_when_auth_fails():
    """connect() returns False when auth_test() responds with ok=False."""
    svc = _make_service()

    mock_web_client = AsyncMock()
    mock_web_client.auth_test = AsyncMock(return_value={"ok": False})

    with patch(
        "clarity_backend.services.slack.AsyncWebClient", return_value=mock_web_client
    ):
        with patch("clarity_backend.services.slack.SocketModeClient", return_value=MagicMock()):
            result = await svc.connect()

    assert result is False


async def test_connect_returns_false_on_exception():
    """connect() returns False when auth_test() raises an exception."""
    svc = _make_service()

    mock_web_client = AsyncMock()
    mock_web_client.auth_test = AsyncMock(side_effect=Exception("slack down"))

    with patch(
        "clarity_backend.services.slack.AsyncWebClient", return_value=mock_web_client
    ):
        with patch("clarity_backend.services.slack.SocketModeClient", return_value=MagicMock()):
            result = await svc.connect()

    assert result is False


# ---------------------------------------------------------------------------
# disconnect()
# ---------------------------------------------------------------------------


async def test_disconnect_closes_socket_client():
    """disconnect() calls close() on the socket client."""
    svc = _make_service()
    mock_socket = AsyncMock()
    mock_socket.socket_mode_request_listeners = []
    svc._socket_client = mock_socket

    await svc.disconnect()

    mock_socket.close.assert_awaited_once()


async def test_disconnect_removes_event_handler():
    """disconnect() removes the registered handler from listeners list."""
    svc = _make_service()
    handler = MagicMock()
    mock_socket = AsyncMock()
    mock_socket.socket_mode_request_listeners = [handler]
    svc._socket_client = mock_socket
    svc._event_handler = handler

    await svc.disconnect()

    assert handler not in mock_socket.socket_mode_request_listeners


async def test_disconnect_does_nothing_when_no_socket_client():
    """disconnect() completes without error when _socket_client is None."""
    svc = _make_service()
    svc._socket_client = None
    await svc.disconnect()  # should not raise


# ---------------------------------------------------------------------------
# fetch_recent()
# ---------------------------------------------------------------------------


async def test_fetch_recent_returns_empty_when_not_connected():
    """fetch_recent() returns [] when _web_client is None."""
    svc = _make_service()
    result = await svc.fetch_recent()
    assert result == []


async def test_fetch_recent_returns_notifications_from_dm_channels():
    """fetch_recent() converts DM messages into Notification objects."""
    svc = _make_service()
    msg = _make_message(text="Hey!", ts="1741000000.000100")

    mock_web_client = AsyncMock()
    # conversations_list for DMs
    mock_web_client.conversations_list = AsyncMock(
        side_effect=[
            {"channels": [{"id": "DM001"}]},      # DM call
            {"channels": []},                       # channel call
        ]
    )
    mock_web_client.conversations_history = AsyncMock(return_value={"messages": [msg]})
    mock_web_client.users_info = AsyncMock(
        return_value={"user": {"profile": {"display_name": "Alice"}, "real_name": "Alice Real"}}
    )
    mock_web_client.conversations_info = AsyncMock(
        return_value={"channel": {"name": "dm-channel"}}
    )

    svc._web_client = mock_web_client
    result = await svc.fetch_recent(limit=10)

    assert len(result) >= 1
    assert result[0].source == Source.SLACK


async def test_fetch_recent_returns_empty_on_complete_failure():
    """fetch_recent() returns [] when all API calls raise exceptions."""
    svc = _make_service()

    mock_web_client = AsyncMock()
    mock_web_client.conversations_list = AsyncMock(side_effect=Exception("API down"))
    svc._web_client = mock_web_client

    result = await svc.fetch_recent()
    assert result == []


async def test_fetch_recent_respects_limit():
    """fetch_recent() caps returned notifications at the requested limit."""
    svc = _make_service()

    # 10 DM channels, each with 1 message
    channels = [{"id": f"DM{i:03d}"} for i in range(10)]
    messages = [_make_message(ts=f"174100000{i}.000100") for i in range(10)]

    mock_web_client = AsyncMock()
    mock_web_client.conversations_list = AsyncMock(
        side_effect=[
            {"channels": channels},
            {"channels": []},
        ]
    )
    mock_web_client.conversations_history = AsyncMock(
        return_value={"messages": [messages[0]]}
    )
    mock_web_client.users_info = AsyncMock(
        return_value={"user": {"profile": {"display_name": "Alice"}, "real_name": "Alice"}}
    )
    mock_web_client.conversations_info = AsyncMock(
        return_value={"channel": {"name": "some-channel"}}
    )

    svc._web_client = mock_web_client
    result = await svc.fetch_recent(limit=3)

    assert len(result) <= 3


# ---------------------------------------------------------------------------
# _message_to_notification()
# ---------------------------------------------------------------------------


async def test_message_to_notification_regular_channel_message():
    """_message_to_notification builds a correct Notification for a channel message."""
    svc = _make_service()
    msg = _make_message(user="U001", text="Hello channel", ts="1741000000.000100")

    mock_web_client = AsyncMock()
    mock_web_client.users_info = AsyncMock(
        return_value={"user": {"profile": {"display_name": "Alice"}, "real_name": "Alice Real"}}
    )
    mock_web_client.conversations_info = AsyncMock(
        return_value={"channel": {"name": "general"}}
    )
    svc._web_client = mock_web_client

    notif = await svc._message_to_notification(msg, "C001", is_dm=False)

    assert notif is not None
    assert notif.source == Source.SLACK
    assert notif.source_account == "test-workspace"
    assert notif.source_id == "C001:1741000000.000100"
    assert notif.notification_type == NotificationType.MESSAGE
    assert notif.title == " #general"
    assert notif.body == "Hello channel"
    assert notif.sender_name == "Alice"
    assert notif.priority == Priority.NORMAL


async def test_message_to_notification_dm():
    """_message_to_notification sets title to 'DM from <sender>' for direct messages."""
    svc = _make_service()
    msg = _make_message(user="U002", text="Hey", ts="1741000001.000100")

    mock_web_client = AsyncMock()
    mock_web_client.users_info = AsyncMock(
        return_value={"user": {"profile": {"display_name": "Bob"}, "real_name": "Bob Real"}}
    )
    mock_web_client.conversations_info = AsyncMock(
        return_value={"channel": {"name": "dm-channel"}}
    )
    svc._web_client = mock_web_client

    notif = await svc._message_to_notification(msg, "DM001", is_dm=True)

    assert notif is not None
    assert notif.title == "DM from Bob"


async def test_message_to_notification_mention_has_high_priority():
    """_message_to_notification sets HIGH priority and MENTION type for mentions."""
    svc = _make_service()
    msg = _make_message(user="U003", text="<@UBOT> help", ts="1741000002.000100")

    mock_web_client = AsyncMock()
    mock_web_client.users_info = AsyncMock(
        return_value={"user": {"profile": {"display_name": "Carol"}, "real_name": "Carol"}}
    )
    mock_web_client.conversations_info = AsyncMock(
        return_value={"channel": {"name": "random"}}
    )
    svc._web_client = mock_web_client

    notif = await svc._message_to_notification(
        msg, "C002", is_dm=False, is_mention=True
    )

    assert notif is not None
    assert notif.notification_type == NotificationType.MENTION
    assert notif.priority == Priority.HIGH


async def test_message_to_notification_thread_id_set_for_threaded_reply():
    """_message_to_notification populates thread_id for messages in a thread."""
    svc = _make_service()
    msg = _make_message(
        user="U004",
        ts="1741000003.000100",
        thread_ts="1741000000.000001",
    )

    mock_web_client = AsyncMock()
    mock_web_client.users_info = AsyncMock(
        return_value={"user": {"profile": {"display_name": "Dave"}, "real_name": "Dave"}}
    )
    mock_web_client.conversations_info = AsyncMock(
        return_value={"channel": {"name": "dev"}}
    )
    svc._web_client = mock_web_client

    notif = await svc._message_to_notification(msg, "C003")

    assert notif is not None
    assert notif.thread_id == "1741000000.000001"


async def test_message_to_notification_body_truncated_to_500():
    """_message_to_notification truncates message body to 500 characters."""
    svc = _make_service()
    msg = _make_message(text="x" * 700)

    mock_web_client = AsyncMock()
    mock_web_client.users_info = AsyncMock(
        return_value={"user": {"profile": {"display_name": "Eve"}, "real_name": "Eve"}}
    )
    mock_web_client.conversations_info = AsyncMock(
        return_value={"channel": {"name": "chan"}}
    )
    svc._web_client = mock_web_client

    notif = await svc._message_to_notification(msg, "C004")

    assert notif is not None
    assert len(notif.body) <= 500


async def test_message_to_notification_returns_none_on_exception():
    """_message_to_notification returns None when an unexpected error occurs."""
    svc = _make_service()
    msg = _make_message()

    mock_web_client = AsyncMock()
    mock_web_client.users_info = AsyncMock(side_effect=Exception("user API down"))
    svc._web_client = mock_web_client

    notif = await svc._message_to_notification(msg, "C005")

    assert notif is None


async def test_message_to_notification_raw_payload_contains_channel_and_ts():
    """raw_payload includes channel_id and ts for reference."""
    svc = _make_service()
    msg = _make_message(ts="1741000099.000100")

    mock_web_client = AsyncMock()
    mock_web_client.users_info = AsyncMock(
        return_value={"user": {"profile": {"display_name": "Frank"}, "real_name": "Frank"}}
    )
    mock_web_client.conversations_info = AsyncMock(
        return_value={"channel": {"name": "eng"}}
    )
    svc._web_client = mock_web_client

    notif = await svc._message_to_notification(msg, "C006")

    assert notif is not None
    assert notif.raw_payload["channel_id"] == "C006"
    assert notif.raw_payload["ts"] == "1741000099.000100"


# ---------------------------------------------------------------------------
# _resolve_user() and _resolve_channel()
# ---------------------------------------------------------------------------


async def test_resolve_user_caches_result():
    """_resolve_user() returns the cached name on the second call."""
    svc = _make_service()

    mock_web_client = AsyncMock()
    mock_web_client.users_info = AsyncMock(
        return_value={"user": {"profile": {"display_name": "Grace"}, "real_name": "Grace"}}
    )
    svc._web_client = mock_web_client

    name1 = await svc._resolve_user("U010")
    name2 = await svc._resolve_user("U010")

    assert name1 == "Grace"
    assert name2 == "Grace"
    mock_web_client.users_info.assert_awaited_once()  # second call hits cache


async def test_resolve_user_falls_back_to_user_id_on_error():
    """_resolve_user() returns the user_id when the API call fails."""
    svc = _make_service()

    mock_web_client = AsyncMock()
    mock_web_client.users_info = AsyncMock(side_effect=Exception("not found"))
    svc._web_client = mock_web_client

    name = await svc._resolve_user("U999")
    assert name == "U999"


async def test_resolve_channel_caches_result():
    """_resolve_channel() returns the cached name on the second call."""
    svc = _make_service()

    mock_web_client = AsyncMock()
    mock_web_client.conversations_info = AsyncMock(
        return_value={"channel": {"name": "general"}}
    )
    svc._web_client = mock_web_client

    name1 = await svc._resolve_channel("C010")
    name2 = await svc._resolve_channel("C010")

    assert name1 == "general"
    assert name2 == "general"
    mock_web_client.conversations_info.assert_awaited_once()
