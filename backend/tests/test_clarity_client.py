"""Tests for ClarityClient and _get_clarity_client helper."""

import os
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DOTENV_CONFIG", "1")

from clarity_backend.integrations.clarity import (  # noqa: E402
    ClarityClient,
    ClarityOfflineError,
    _get_clarity_client,
)


def _make_mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    return resp


def _patch_async_client(mock_response: MagicMock):
    """Return a context manager patch that injects mock_response into httpx.AsyncClient."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.post = AsyncMock(return_value=mock_response)

    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_context.__aexit__ = AsyncMock(return_value=False)

    return mock_context, mock_client


class TestClarityClientHeaders:
    def test_headers_include_api_key(self):
        client = ClarityClient(base_url="http://example.com", api_key="secret-key-123")
        assert client._headers["X-API-Key"] == "secret-key-123"
        assert client._headers["Content-Type"] == "application/json"

    def test_base_url_strips_trailing_slash(self):
        client = ClarityClient(base_url="http://example.com/", api_key="key")
        assert client.base_url == "http://example.com"

    def test_base_url_strips_multiple_trailing_slashes(self):
        client = ClarityClient(base_url="http://example.com///", api_key="key")
        assert client.base_url == "http://example.com"

    def test_base_url_without_slash_unchanged(self):
        client = ClarityClient(base_url="http://example.com", api_key="key")
        assert client.base_url == "http://example.com"


class TestClarityClientGetScheduleDashboard:
    @pytest.mark.asyncio
    async def test_get_schedule_dashboard_success(self):
        expected = {"client": "novachem", "schedules": [{"id": 1, "status": "active"}]}
        mock_response = _make_mock_response(expected)
        mock_context, mock_client = _patch_async_client(mock_response)

        with patch("httpx.AsyncClient", return_value=mock_context):
            client = ClarityClient(base_url="http://clarity.test", api_key="key")
            result = await client.get_schedule_dashboard(client_id="novachem")

        assert result == expected
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "novachem" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_schedule_dashboard_default_client(self):
        expected = {"schedules": []}
        mock_response = _make_mock_response(expected)
        mock_context, mock_client = _patch_async_client(mock_response)

        with patch("httpx.AsyncClient", return_value=mock_context):
            client = ClarityClient(base_url="http://clarity.test", api_key="key")
            result = await client.get_schedule_dashboard()

        assert result == expected
        assert "default" in mock_client.get.call_args[0][0]


class TestClarityClientCreateParkingLotItem:
    @pytest.mark.asyncio
    async def test_create_parking_lot_item_success(self):
        expected = {"id": 42, "content": "buy milk", "status": "pending"}
        mock_response = _make_mock_response(expected)
        mock_context, mock_client = _patch_async_client(mock_response)

        with patch("httpx.AsyncClient", return_value=mock_context):
            client = ClarityClient(base_url="http://clarity.test", api_key="key")
            result = await client.create_parking_lot_item(content="buy milk")

        assert result == expected
        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["json"] == {"content": "buy milk"}

    @pytest.mark.asyncio
    async def test_create_parking_lot_item_sends_correct_url(self):
        mock_response = _make_mock_response({"id": 1})
        mock_context, mock_client = _patch_async_client(mock_response)

        with patch("httpx.AsyncClient", return_value=mock_context):
            client = ClarityClient(base_url="http://clarity.test", api_key="mykey")
            await client.create_parking_lot_item(content="test item")

        url = mock_client.post.call_args[0][0]
        assert url == "http://clarity.test/api/adhd/parking-lot/"


class TestClarityClientErrorHandling:
    @pytest.mark.asyncio
    async def test_connection_error_raises_clarity_offline(self):
        mock_context = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_context):
            client = ClarityClient(base_url="http://clarity.test", api_key="key")
            with pytest.raises(ClarityOfflineError):
                await client.get_schedule_dashboard()

    @pytest.mark.asyncio
    async def test_timeout_raises_clarity_offline(self):
        mock_context = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectTimeout("timed out"))
        mock_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_context):
            client = ClarityClient(base_url="http://clarity.test", api_key="key")
            with pytest.raises(ClarityOfflineError):
                await client.get_unified_inbox()

    @pytest.mark.asyncio
    async def test_post_connection_error_raises_clarity_offline(self):
        mock_context = MagicMock()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_context):
            client = ClarityClient(base_url="http://clarity.test", api_key="key")
            with pytest.raises(ClarityOfflineError):
                await client.create_parking_lot_item(content="test")


class TestGetClarityClientHelper:
    def test_get_clarity_client_uses_settings_url_and_key(self):
        fake_settings = {"clarity_api_url": "http://fake-clarity.io", "clarity_api_key": "fake-key"}

        with patch(
            "clarity_backend.settings.manager._read_settings",
            return_value=fake_settings,
        ):
            client = _get_clarity_client()

        assert client.base_url == "http://fake-clarity.io"
        assert client.api_key == "fake-key"

    def test_get_clarity_client_falls_back_to_env_settings(self):
        empty_settings: dict = {}

        from clarity_backend.config import settings as env_settings

        original_url = env_settings.CLARITY_API_URL
        original_key = env_settings.CLARITY_API_KEY

        env_settings.CLARITY_API_URL = "http://env-clarity.io"
        env_settings.CLARITY_API_KEY = "env-api-key"
        try:
            with patch(
                "clarity_backend.settings.manager._read_settings",
                return_value=empty_settings,
            ):
                client = _get_clarity_client()
        finally:
            env_settings.CLARITY_API_URL = original_url
            env_settings.CLARITY_API_KEY = original_key

        assert isinstance(client, ClarityClient)
        assert client.base_url == "http://env-clarity.io"
        assert client.api_key == "env-api-key"
