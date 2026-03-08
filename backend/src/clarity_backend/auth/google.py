import asyncio
import secrets
import time
from collections import OrderedDict

import httpx
from google_auth_oauthlib.flow import Flow

from clarity_backend.auth.tokens import load_tokens as _load_tokens
from clarity_backend.auth.tokens import save_tokens as _save_tokens
from clarity_backend.config import settings

GMAIL_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]

# Maps state token → (code_verifier, timestamp). TTL = 10 minutes.
_STATE_TTL = 600
_pending_states: OrderedDict[str, tuple[str, float]] = OrderedDict()


def _cleanup_expired_states() -> None:
    now = time.time()
    while _pending_states:
        _state, (_, ts) = next(iter(_pending_states.items()))
        if now - ts > _STATE_TTL:
            _pending_states.pop(_state)
        else:
            break


def _make_client_config() -> dict:
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }


def build_auth_url() -> str:
    _cleanup_expired_states()
    state = secrets.token_urlsafe(32)
    flow = Flow.from_client_config(
        _make_client_config(),
        scopes=GMAIL_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline", prompt="consent", state=state
    )
    # Store the PKCE code_verifier so exchange_code() can use it
    _pending_states[state] = (flow.code_verifier, time.time())
    return auth_url


def validate_and_consume_state(state: str) -> str | None:
    """Pop and return the code_verifier for this state, or None if invalid/expired."""
    entry = _pending_states.pop(state, None)
    if entry is None:
        return None
    verifier, ts = entry
    if time.time() - ts > _STATE_TTL:
        return None
    return verifier


async def exchange_code(code: str, code_verifier: str) -> dict:
    def _exchange():
        flow = Flow.from_client_config(
            _make_client_config(),
            scopes=GMAIL_SCOPES,
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
        )
        flow.code_verifier = code_verifier
        flow.fetch_token(code=code)
        creds = flow.credentials
        return {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "expires_at": creds.expiry.isoformat() if creds.expiry else None,
        }

    return await asyncio.to_thread(_exchange)


async def get_user_email(access_token: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()["email"]


async def save_tokens(email: str, tokens: dict) -> None:
    await _save_tokens("gmail", email, tokens)


async def load_tokens(email: str) -> dict | None:
    return await _load_tokens("gmail", email)
