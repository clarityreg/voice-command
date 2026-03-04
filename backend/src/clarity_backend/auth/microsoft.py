import secrets

import httpx
import msal

from clarity_backend.auth.tokens import load_tokens as _load_tokens
from clarity_backend.auth.tokens import save_tokens as _save_tokens
from clarity_backend.config import settings

MS_SCOPES = ["User.Read", "Mail.ReadWrite", "Mail.Send"]

_pending_states: dict[str, bool] = {}
_msal_app: msal.ConfidentialClientApplication | None = None


def _get_msal_app() -> msal.ConfidentialClientApplication:
    global _msal_app
    if _msal_app is None:
        _msal_app = msal.ConfidentialClientApplication(
            settings.MS_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}",
            client_credential=settings.MS_CLIENT_SECRET,
        )
    return _msal_app


def build_auth_url() -> str:
    state = secrets.token_urlsafe(32)
    _pending_states[state] = True
    app = _get_msal_app()
    return app.get_authorization_request_url(
        scopes=MS_SCOPES, state=state, redirect_uri=settings.MS_REDIRECT_URI
    )


def validate_and_consume_state(state: str) -> bool:
    return _pending_states.pop(state, False)


def exchange_code(code: str) -> dict:
    app = _get_msal_app()
    result = app.acquire_token_by_authorization_code(
        code, scopes=MS_SCOPES, redirect_uri=settings.MS_REDIRECT_URI
    )
    if "access_token" not in result:
        error = result.get("error_description", result.get("error", "Unknown error"))
        raise ValueError(f"Token exchange failed: {error}")
    return {
        "access_token": result["access_token"],
        "refresh_token": result.get("refresh_token", ""),
        "expires_at": None,
    }


async def get_user_email(access_token: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("mail") or data.get("userPrincipalName", "")


async def save_tokens(email: str, tokens: dict) -> None:
    await _save_tokens("outlook", email, tokens)


async def load_tokens(email: str) -> dict | None:
    return await _load_tokens("outlook", email)
