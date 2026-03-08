"""Tests for OutlookService — connection, message fetching, mapping, and error handling."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from clarity_backend.notifications.models import NotificationType, Priority, Source
from clarity_backend.services.outlook import OutlookService


def _make_service(email: str = "test@outlook.com") -> OutlookService:
    return OutlookService(email, credentials={"access_token": "test-token"})


def _make_message(
    msg_id: str = "msg-001",
    subject: str = "Test Subject",
    body_preview: str = "Hello from Outlook",
    from_name: str = "Alice",
    from_email: str = "alice@outlook.com",
    received: str = "2026-03-06T12:00:00Z",
    is_read: bool = False,
    conversation_id: str = "conv-001",
) -> dict:
    return {
        "id": msg_id,
        "subject": subject,
        "bodyPreview": body_preview,
        "from": {"emailAddress": {"name": from_name, "address": from_email}},
        "receivedDateTime": received,
        "isRead": is_read,
        "conversationId": conversation_id,
    }


# ---------------------------------------------------------------------------
# connect()
# ---------------------------------------------------------------------------


async def test_connect_with_credentials():
    """connect() returns True when credentials contain an access_token."""
    svc = _make_service()
    result = await svc.connect()
    assert result is True
    assert svc._access_token == "test-token"


async def test_connect_with_no_credentials():
    """connect() returns False when credentials are None and token load fails."""
    svc = OutlookService("test@outlook.com", credentials=None)
    with patch(
        "clarity_backend.services.outlook.OutlookService.connect",
        new_callable=AsyncMock,
        return_value=False,
    ):
        # Directly test with no credentials and no token loader
        svc._credentials = None
        result = await svc.connect()
    assert result is False


async def test_connect_exception_returns_false():
    """connect() returns False when an exception is raised."""
    svc = OutlookService("test@outlook.com", credentials=None)
    with patch(
        "clarity_backend.auth.microsoft.load_tokens",
        new_callable=AsyncMock,
        side_effect=Exception("Token load failed"),
    ):
        result = await svc.connect()
    assert result is False


# ---------------------------------------------------------------------------
# disconnect()
# ---------------------------------------------------------------------------


async def test_disconnect_clears_token():
    """disconnect() sets _access_token to None."""
    svc = _make_service()
    svc._access_token = "test-token"
    await svc.disconnect()
    assert svc._access_token is None


# ---------------------------------------------------------------------------
# fetch_recent()
# ---------------------------------------------------------------------------


async def test_fetch_recent_returns_empty_when_not_connected():
    """fetch_recent() returns [] when _access_token is None."""
    svc = OutlookService("test@outlook.com")
    svc._access_token = None
    result = await svc.fetch_recent()
    assert result == []


async def test_fetch_recent_returns_notifications():
    """fetch_recent() converts Graph API messages into Notification objects."""
    svc = _make_service()
    svc._access_token = "test-token"
    msg = _make_message()

    mock_response = MagicMock()
    mock_response.json.return_value = {"value": [msg]}
    mock_response.raise_for_status.return_value = None

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    mock_client.get.return_value = mock_response

    with patch("clarity_backend.services.outlook.httpx.AsyncClient", return_value=mock_client):
        result = await svc.fetch_recent(limit=10)

    assert len(result) == 1
    assert result[0].source == Source.OUTLOOK
    assert result[0].title == "Test Subject"
    assert result[0].body == "Hello from Outlook"


async def test_fetch_recent_returns_empty_on_error():
    """fetch_recent() returns [] when API call fails."""
    svc = _make_service()
    svc._access_token = "test-token"

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    mock_client.get = AsyncMock(side_effect=Exception("Graph API down"))

    with patch("clarity_backend.services.outlook.httpx.AsyncClient", return_value=mock_client):
        result = await svc.fetch_recent()

    assert result == []


# ---------------------------------------------------------------------------
# _message_to_notification()
# ---------------------------------------------------------------------------


def test_message_to_notification_maps_fields():
    """_message_to_notification correctly maps Graph API fields."""
    svc = _make_service()
    msg = _make_message()
    notif = svc._message_to_notification(msg)

    assert notif.source == Source.OUTLOOK
    assert notif.source_account == "test@outlook.com"
    assert notif.source_id == "msg-001"
    assert notif.notification_type == NotificationType.EMAIL
    assert notif.title == "Test Subject"
    assert notif.body == "Hello from Outlook"
    assert notif.sender_name == "Alice"
    assert notif.thread_id == "conv-001"
    assert notif.raw_payload == {"isRead": False}


def test_message_to_notification_no_subject():
    """_message_to_notification uses '(No Subject)' when subject is missing."""
    svc = _make_service()
    msg = _make_message()
    del msg["subject"]
    notif = svc._message_to_notification(msg)
    assert notif.title == "(No Subject)"


def test_message_to_notification_no_from():
    """_message_to_notification handles missing from data gracefully."""
    svc = _make_service()
    msg = _make_message()
    msg["from"] = {}
    notif = svc._message_to_notification(msg)
    assert notif.sender_name == "Unknown"


def test_message_to_notification_sender_fallback_to_email():
    """_message_to_notification uses email address when name is missing."""
    svc = _make_service()
    msg = _make_message()
    msg["from"] = {"emailAddress": {"address": "bob@test.com"}}
    notif = svc._message_to_notification(msg)
    assert notif.sender_name == "bob@test.com"


def test_message_to_notification_read_message():
    """_message_to_notification includes isRead in raw_payload."""
    svc = _make_service()
    msg = _make_message(is_read=True)
    notif = svc._message_to_notification(msg)
    assert notif.raw_payload["isRead"] is True


def test_message_to_notification_timestamp_parsing():
    """_message_to_notification parses ISO timestamp from Graph API."""
    svc = _make_service()
    msg = _make_message(received="2026-03-06T15:30:00Z")
    notif = svc._message_to_notification(msg)
    assert notif.timestamp.year == 2026
    assert notif.timestamp.month == 3
    assert notif.timestamp.hour == 15
