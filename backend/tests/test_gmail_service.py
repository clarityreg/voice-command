"""Tests for GmailService — connection, message fetching, mapping, and error handling."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from clarity_backend.notifications.models import NotificationType, Source
from clarity_backend.services.gmail import GmailService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_message(
    msg_id: str = "msg-001",
    subject: str = "Hello World",
    sender: str = "Alice <alice@example.com>",
    date: str = "Mon, 10 Mar 2026 09:00:00 +0000",
    snippet: str = "Hi there!",
    labels: list | None = None,
    thread_id: str = "thread-001",
) -> dict:
    """Build a fake Gmail message API response."""
    return {
        "id": msg_id,
        "threadId": thread_id,
        "snippet": snippet,
        "labelIds": labels or ["INBOX", "UNREAD"],
        "payload": {
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": sender},
                {"name": "Date", "value": date},
            ]
        },
    }


def _make_credentials(expired: bool = False) -> dict:
    return {
        "access_token": "access-tok",
        "refresh_token": "refresh-tok",
        "expires_at": "2026-01-01T00:00:00" if expired else "2030-01-01T00:00:00",
    }


def _mock_google_creds(expired: bool = False):
    """Return a MagicMock that mimics google.oauth2.credentials.Credentials."""
    creds = MagicMock()
    creds.expired = expired
    creds.refresh_token = "refresh-tok"
    creds.token = "access-tok"
    creds.expiry = None
    return creds


# ---------------------------------------------------------------------------
# connect()
# ---------------------------------------------------------------------------


async def test_connect_success_with_provided_credentials():
    """connect() returns True when valid credentials are passed directly."""
    mock_creds = _mock_google_creds(expired=False)

    with patch("clarity_backend.services.gmail.Credentials", return_value=mock_creds):
        with patch("clarity_backend.services.gmail.build") as mock_build:
            mock_build.return_value = MagicMock()
            svc = GmailService("user@example.com", credentials=_make_credentials())
            result = await svc.connect()

    assert result is True
    assert svc._gmail_client is not None
    mock_build.assert_called_once_with("gmail", "v1", credentials=mock_creds)


async def test_connect_loads_tokens_when_no_credentials():
    """connect() calls load_tokens when no credentials are provided."""
    mock_creds = _mock_google_creds(expired=False)

    with patch("clarity_backend.services.gmail.Credentials", return_value=mock_creds):
        with patch("clarity_backend.services.gmail.build", return_value=MagicMock()):
            with patch(
                "clarity_backend.auth.google.load_tokens",
                new_callable=AsyncMock,
                return_value=_make_credentials(),
            ):
                svc = GmailService("user@example.com", credentials=None)
                result = await svc.connect()

    assert result is True


async def test_connect_returns_false_when_no_tokens_available():
    """connect() returns False when load_tokens yields nothing."""
    with patch(
        "clarity_backend.auth.google.load_tokens",
        new_callable=AsyncMock,
        return_value=None,
    ):
        svc = GmailService("user@example.com", credentials=None)
        result = await svc.connect()

    assert result is False
    assert svc._gmail_client is None


async def test_connect_refreshes_expired_credentials():
    """connect() refreshes and saves tokens when credentials are expired."""
    mock_creds = _mock_google_creds(expired=True)

    async def mock_run_in_executor(_executor, fn):
        fn()

    with patch("clarity_backend.services.gmail.Credentials", return_value=mock_creds):
        with patch("clarity_backend.services.gmail.build", return_value=MagicMock()):
            with patch(
                "clarity_backend.services.gmail.asyncio.get_event_loop"
            ) as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock(
                    side_effect=mock_run_in_executor
                )
                with patch(
                    "clarity_backend.auth.google.save_tokens", new_callable=AsyncMock
                ) as mock_save:
                    svc = GmailService(
                        "user@example.com", credentials=_make_credentials(expired=True)
                    )
                    result = await svc.connect()

    assert result is True


async def test_connect_returns_false_on_exception():
    """connect() returns False when Credentials() raises."""
    with patch(
        "clarity_backend.services.gmail.Credentials",
        side_effect=Exception("invalid creds"),
    ):
        svc = GmailService("user@example.com", credentials=_make_credentials())
        result = await svc.connect()

    assert result is False


# ---------------------------------------------------------------------------
# disconnect()
# ---------------------------------------------------------------------------


async def test_disconnect_clears_client():
    """disconnect() sets _gmail_client to None."""
    svc = GmailService("user@example.com")
    svc._gmail_client = MagicMock()
    await svc.disconnect()
    assert svc._gmail_client is None


# ---------------------------------------------------------------------------
# fetch_recent()
# ---------------------------------------------------------------------------


async def test_fetch_recent_returns_empty_when_no_client():
    """fetch_recent() returns [] when not connected."""
    svc = GmailService("user@example.com")
    result = await svc.fetch_recent()
    assert result == []


async def test_fetch_recent_returns_notifications():
    """fetch_recent() converts message refs into Notification objects."""
    msg = _make_message()
    profile = {"historyId": "55555"}

    mock_messages_list = MagicMock()
    mock_messages_list.execute.return_value = {"messages": [{"id": "msg-001"}]}

    mock_messages_get = MagicMock()
    mock_messages_get.execute.return_value = msg

    mock_profile = MagicMock()
    mock_profile.execute.return_value = profile

    mock_users = MagicMock()
    mock_users.messages.return_value.list.return_value = mock_messages_list
    mock_users.messages.return_value.get.return_value = mock_messages_get
    mock_users.getProfile.return_value = mock_profile

    mock_client = MagicMock()
    mock_client.users.return_value = mock_users

    async def fake_run_in_executor(_exec, fn):
        return fn()

    svc = GmailService("user@example.com", credentials=_make_credentials())
    svc._gmail_client = mock_client

    with patch(
        "clarity_backend.services.gmail.asyncio.get_event_loop"
    ) as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(side_effect=fake_run_in_executor)
        result = await svc.fetch_recent(limit=5)

    assert len(result) == 1
    assert result[0].source == Source.GMAIL
    assert result[0].source_id == "msg-001"
    assert result[0].title == "Hello World"


async def test_fetch_recent_sets_last_history_id():
    """fetch_recent() captures historyId from the profile call."""
    msg = _make_message()
    profile = {"historyId": "99999"}

    mock_messages_list = MagicMock()
    mock_messages_list.execute.return_value = {"messages": [{"id": "msg-001"}]}

    mock_messages_get = MagicMock()
    mock_messages_get.execute.return_value = msg

    mock_profile = MagicMock()
    mock_profile.execute.return_value = profile

    mock_users = MagicMock()
    mock_users.messages.return_value.list.return_value = mock_messages_list
    mock_users.messages.return_value.get.return_value = mock_messages_get
    mock_users.getProfile.return_value = mock_profile

    mock_client = MagicMock()
    mock_client.users.return_value = mock_users

    async def fake_run_in_executor(_exec, fn):
        return fn()

    svc = GmailService("user@example.com", credentials=_make_credentials())
    svc._gmail_client = mock_client

    with patch(
        "clarity_backend.services.gmail.asyncio.get_event_loop"
    ) as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(side_effect=fake_run_in_executor)
        await svc.fetch_recent()

    assert svc._last_history_id == "99999"


async def test_fetch_recent_returns_empty_on_api_error():
    """fetch_recent() returns [] when the Google API raises an exception."""

    async def fake_run_in_executor(_exec, fn):
        raise Exception("API error")

    svc = GmailService("user@example.com", credentials=_make_credentials())
    svc._gmail_client = MagicMock()

    with patch(
        "clarity_backend.services.gmail.asyncio.get_event_loop"
    ) as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(side_effect=fake_run_in_executor)
        result = await svc.fetch_recent()

    assert result == []


# ---------------------------------------------------------------------------
# _message_to_notification()
# ---------------------------------------------------------------------------


async def test_message_to_notification_maps_fields():
    """_message_to_notification correctly maps header fields to Notification."""
    msg = _make_message(
        msg_id="abc-123",
        subject="Meeting invite",
        sender="Bob Smith <bob@example.com>",
        snippet="Join us at 3pm",
        thread_id="thread-xyz",
    )

    async def fake_run_in_executor(_exec, fn):
        return fn()

    mock_users = MagicMock()
    mock_users.messages.return_value.get.return_value.execute.return_value = msg

    mock_client = MagicMock()
    mock_client.users.return_value = mock_users

    svc = GmailService("user@example.com")
    svc._gmail_client = mock_client

    with patch(
        "clarity_backend.services.gmail.asyncio.get_event_loop"
    ) as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(side_effect=fake_run_in_executor)
        notif = await svc._message_to_notification("abc-123")

    assert notif is not None
    assert notif.source == Source.GMAIL
    assert notif.source_account == "user@example.com"
    assert notif.source_id == "abc-123"
    assert notif.title == "Meeting invite"
    assert notif.body == "Join us at 3pm"
    assert notif.sender_name == "Bob Smith"
    assert notif.thread_id == "thread-xyz"
    assert notif.notification_type == NotificationType.EMAIL


async def test_message_to_notification_handles_no_subject():
    """_message_to_notification uses '(No Subject)' when Subject header is absent."""
    msg = {
        "id": "msg-no-sub",
        "threadId": "t1",
        "snippet": "",
        "labelIds": [],
        "payload": {
            "headers": [{"name": "From", "value": "someone@example.com"}]
        },
    }

    async def fake_run_in_executor(_exec, fn):
        return fn()

    mock_client = MagicMock()
    mock_client.users.return_value.messages.return_value.get.return_value.execute.return_value = msg

    svc = GmailService("user@example.com")
    svc._gmail_client = mock_client

    with patch(
        "clarity_backend.services.gmail.asyncio.get_event_loop"
    ) as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(side_effect=fake_run_in_executor)
        notif = await svc._message_to_notification("msg-no-sub")

    assert notif is not None
    assert notif.title == "(No Subject)"


async def test_message_to_notification_returns_none_on_error():
    """_message_to_notification returns None when the API call raises."""

    async def fake_run_in_executor(_exec, fn):
        raise Exception("API error")

    svc = GmailService("user@example.com")
    svc._gmail_client = MagicMock()

    with patch(
        "clarity_backend.services.gmail.asyncio.get_event_loop"
    ) as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(side_effect=fake_run_in_executor)
        notif = await svc._message_to_notification("bad-id")

    assert notif is None


async def test_message_to_notification_strips_sender_angle_brackets():
    """Sender name is extracted cleanly from 'Name <email>' format."""
    msg = _make_message(sender='"Carol White" <carol@example.com>')

    async def fake_run_in_executor(_exec, fn):
        return fn()

    mock_client = MagicMock()
    mock_client.users.return_value.messages.return_value.get.return_value.execute.return_value = msg

    svc = GmailService("user@example.com")
    svc._gmail_client = mock_client

    with patch(
        "clarity_backend.services.gmail.asyncio.get_event_loop"
    ) as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(side_effect=fake_run_in_executor)
        notif = await svc._message_to_notification("msg-001")

    assert notif is not None
    assert notif.sender_name == "Carol White"


async def test_message_to_notification_raw_payload_contains_labels():
    """raw_payload includes the message's labelIds."""
    msg = _make_message(labels=["INBOX", "UNREAD", "IMPORTANT"])

    async def fake_run_in_executor(_exec, fn):
        return fn()

    mock_client = MagicMock()
    mock_client.users.return_value.messages.return_value.get.return_value.execute.return_value = msg

    svc = GmailService("user@example.com")
    svc._gmail_client = mock_client

    with patch(
        "clarity_backend.services.gmail.asyncio.get_event_loop"
    ) as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(side_effect=fake_run_in_executor)
        notif = await svc._message_to_notification("msg-001")

    assert notif is not None
    assert "IMPORTANT" in notif.raw_payload["labels"]
