"""Tests for the /webhooks/clarity endpoint."""

import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DOTENV_CONFIG", "1")

from clarity_backend.main import app  # noqa: E402

VALID_PAYLOAD = {
    "event_type": "schedule_status_change",
    "title": "Schedule Updated",
    "body": "Client NovaChem schedule moved to active.",
    "id": "evt-001",
    "project_name": "novachem",
}


def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


_SECRET_PATCH = "clarity_backend.webhooks.clarity._get_webhook_secret"
_SAVE_PATCH = "clarity_backend.webhooks.clarity.save_notification"
# ws_manager is imported inside the function body, so patch the actual singleton method.
_WS_PATCH = "clarity_backend.notifications.ws.ws_manager.send_notification"


@pytest.mark.asyncio
async def test_valid_webhook_creates_notification():
    with (
        patch(_SECRET_PATCH, return_value=""),
        patch(_SAVE_PATCH, new_callable=AsyncMock),
        patch(_WS_PATCH, new_callable=AsyncMock),
    ):
        async with _make_client() as client:
            resp = await client.post("/webhooks/clarity", json=VALID_PAYLOAD)

    assert resp.status_code == 200
    assert resp.json() == {"ingested": 1}


@pytest.mark.asyncio
async def test_missing_event_type_returns_400():
    with (
        patch(_SECRET_PATCH, return_value=""),
        patch(_SAVE_PATCH, new_callable=AsyncMock),
    ):
        async with _make_client() as client:
            resp = await client.post("/webhooks/clarity", json={"title": "No event type here"})

    assert resp.status_code == 400
    assert "event_type" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_unknown_event_type_skipped():
    with (
        patch(_SECRET_PATCH, return_value=""),
        patch(_SAVE_PATCH, new_callable=AsyncMock) as mock_save,
    ):
        async with _make_client() as client:
            resp = await client.post(
                "/webhooks/clarity",
                json={"event_type": "totally_unknown_event", "title": "Something"},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["ingested"] == 0
    assert body["skipped"] == "totally_unknown_event"
    mock_save.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_secret_returns_401():
    with patch(_SECRET_PATCH, return_value="correct-secret"):
        async with _make_client() as client:
            resp = await client.post(
                "/webhooks/clarity",
                json=VALID_PAYLOAD,
                headers={"x-webhook-secret": "wrong-secret"},
            )

    assert resp.status_code == 401
    assert "secret" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_missing_secret_header_returns_401_when_secret_configured():
    with patch(_SECRET_PATCH, return_value="configured-secret"):
        async with _make_client() as client:
            resp = await client.post("/webhooks/clarity", json=VALID_PAYLOAD)

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_no_secret_configured_allows_all():
    with (
        patch(_SECRET_PATCH, return_value=""),
        patch(_SAVE_PATCH, new_callable=AsyncMock),
        patch(_WS_PATCH, new_callable=AsyncMock),
    ):
        async with _make_client() as client:
            resp = await client.post("/webhooks/clarity", json=VALID_PAYLOAD)

    assert resp.status_code == 200
    assert resp.json()["ingested"] == 1


@pytest.mark.asyncio
async def test_correct_secret_allows_request():
    with (
        patch(_SECRET_PATCH, return_value="my-secret"),
        patch(_SAVE_PATCH, new_callable=AsyncMock),
        patch(_WS_PATCH, new_callable=AsyncMock),
    ):
        async with _make_client() as client:
            resp = await client.post(
                "/webhooks/clarity",
                json=VALID_PAYLOAD,
                headers={"x-webhook-secret": "my-secret"},
            )

    assert resp.status_code == 200
    assert resp.json()["ingested"] == 1


@pytest.mark.asyncio
async def test_action_point_created_event():
    payload = {
        "event_type": "action_point_created",
        "title": "New action point",
        "body": "Review compliance doc",
        "id": "ap-042",
    }
    with (
        patch(_SECRET_PATCH, return_value=""),
        patch(_SAVE_PATCH, new_callable=AsyncMock) as mock_save,
        patch(_WS_PATCH, new_callable=AsyncMock),
    ):
        async with _make_client() as client:
            resp = await client.post("/webhooks/clarity", json=payload)

    assert resp.status_code == 200
    assert resp.json()["ingested"] == 1
    _, saved_notification = mock_save.call_args[0]
    assert saved_notification.title == "New action point"
    assert saved_notification.source_id == "ap-042"


@pytest.mark.asyncio
async def test_review_overdue_event():
    payload = {
        "event_type": "review_overdue",
        "title": "Review overdue alert",
        "description": "Product review is 3 days overdue.",
        "event_id": "rev-007",
    }
    with (
        patch(_SECRET_PATCH, return_value=""),
        patch(_SAVE_PATCH, new_callable=AsyncMock),
        patch(_WS_PATCH, new_callable=AsyncMock),
    ):
        async with _make_client() as client:
            resp = await client.post("/webhooks/clarity", json=payload)

    assert resp.status_code == 200
    assert resp.json()["ingested"] == 1


@pytest.mark.asyncio
async def test_notification_title_defaults_to_event_type_when_missing():
    payload = {"event_type": "compliance_failed", "id": "cf-001"}
    with (
        patch(_SECRET_PATCH, return_value=""),
        patch(_SAVE_PATCH, new_callable=AsyncMock) as mock_save,
        patch(_WS_PATCH, new_callable=AsyncMock),
    ):
        async with _make_client() as client:
            resp = await client.post("/webhooks/clarity", json=payload)

    assert resp.status_code == 200
    _, saved_notification = mock_save.call_args[0]
    assert "compliance_failed" in saved_notification.title
