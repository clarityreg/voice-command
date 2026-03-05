"""Tests for OAuth auth routes — Google and Microsoft.

Covers the 500-error path for Gmail account connection and validates
all auth endpoints handle edge cases correctly.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# GET /auth/google/start
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_google_start_redirects(client: AsyncClient, monkeypatch):
    """Should redirect to Google when credentials are configured."""
    from clarity_backend import config

    monkeypatch.setattr(config.settings, "GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setattr(config.settings, "GOOGLE_CLIENT_SECRET", "test-secret")

    with patch(
        "clarity_backend.auth.google.build_auth_url",
        return_value="https://accounts.google.com/o/oauth2/auth?client_id=test",
    ):
        resp = await client.get("/auth/google/start", follow_redirects=False)

    assert resp.status_code == 307
    assert "accounts.google.com" in resp.headers["location"]


@pytest.mark.asyncio
async def test_google_start_500_when_not_configured(client: AsyncClient):
    """Should return 500 when Google OAuth is not configured."""
    with patch("clarity_backend.auth.routes.settings") as mock_settings:
        mock_settings.GOOGLE_CLIENT_ID = ""
        mock_settings.GOOGLE_CLIENT_SECRET = ""

        resp = await client.get("/auth/google/start")

    assert resp.status_code == 500
    assert "not configured" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# GET /auth/google/callback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_google_callback_invalid_state(client: AsyncClient):
    """Should return 400 for empty state token."""
    resp = await client.get("/auth/google/callback?code=testcode&state=")
    assert resp.status_code == 400
    assert "Invalid or expired state" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_google_callback_expired_state(client: AsyncClient):
    """Should return 400 for a state token that was never issued (returns None)."""
    with patch(
        "clarity_backend.auth.google.validate_and_consume_state",
        return_value=None,
    ):
        resp = await client.get("/auth/google/callback?code=testcode&state=bogus-state")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_google_callback_success(client: AsyncClient):
    """Should exchange code, save tokens, and return success HTML."""
    mock_tokens = {
        "access_token": "ya29.test",
        "refresh_token": "1//test-refresh",
        "expires_at": "2026-12-31T00:00:00",
    }

    with (
        patch(
            "clarity_backend.auth.google.validate_and_consume_state",
            return_value="test-code-verifier",
        ),
        patch(
            "clarity_backend.auth.google.exchange_code",
            new_callable=AsyncMock,
            return_value=mock_tokens,
        ) as mock_exchange,
        patch(
            "clarity_backend.auth.google.get_user_email",
            new_callable=AsyncMock,
            return_value="user@gmail.com",
        ),
        patch(
            "clarity_backend.auth.google.save_tokens",
            new_callable=AsyncMock,
        ) as mock_save,
        patch("clarity_backend.services.registry.registry") as mock_registry,
    ):
        mock_registry.add_gmail_service = AsyncMock()
        resp = await client.get(
            "/auth/google/callback?code=4/test-code&state=valid-state"
        )

    assert resp.status_code == 200
    assert "Gmail Connected" in resp.text
    assert "user@gmail.com" in resp.text
    # Verify code_verifier is passed through to exchange_code
    mock_exchange.assert_awaited_once_with("4/test-code", "test-code-verifier")
    mock_save.assert_awaited_once_with("user@gmail.com", mock_tokens)
    mock_registry.add_gmail_service.assert_awaited_once()


@pytest.mark.asyncio
async def test_google_callback_exchange_failure(client: AsyncClient):
    """Should return 500 when token exchange fails (the actual 500 bug)."""
    with (
        patch(
            "clarity_backend.auth.google.validate_and_consume_state",
            return_value="test-verifier",
        ),
        patch(
            "clarity_backend.auth.google.exchange_code",
            new_callable=AsyncMock,
            side_effect=Exception("Token exchange error: invalid_grant"),
        ),
    ):
        resp = await client.get(
            "/auth/google/callback?code=expired-code&state=valid-state"
        )

    assert resp.status_code == 500
    assert "OAuth token exchange failed" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_google_callback_missing_code(client: AsyncClient):
    """Should return 422 when code param is missing."""
    resp = await client.get("/auth/google/callback?state=something")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/auth/gmail/{email}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_remove_gmail_account_not_found(client: AsyncClient):
    """Should return 404 when email has no stored tokens or active service."""
    with patch("clarity_backend.services.registry.registry") as mock_reg:
        mock_reg.remove_gmail_service = AsyncMock(return_value=False)
        resp = await client.delete("/api/auth/gmail/nobody@test.com")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_remove_gmail_account_success(client: AsyncClient):
    """Should return success when service or tokens exist."""
    with patch("clarity_backend.services.registry.registry") as mock_reg:
        mock_reg.remove_gmail_service = AsyncMock(return_value=True)
        resp = await client.delete("/api/auth/gmail/user@test.com")

    assert resp.status_code == 200
    assert resp.json()["status"] == "removed"


# ---------------------------------------------------------------------------
# GET /auth/microsoft/start
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_microsoft_start_500_when_not_configured(client: AsyncClient):
    """Should return 500 when Microsoft OAuth is not configured."""
    with patch("clarity_backend.auth.routes.settings") as mock_settings:
        mock_settings.MS_CLIENT_ID = ""
        mock_settings.MS_CLIENT_SECRET = ""

        resp = await client.get("/auth/microsoft/start")

    assert resp.status_code == 500
    assert "not configured" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# GET /auth/microsoft/callback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_microsoft_callback_invalid_state(client: AsyncClient):
    """Should return 400 for invalid state."""
    resp = await client.get("/auth/microsoft/callback?code=testcode&state=")
    assert resp.status_code == 400
