import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from clarity_backend.config import settings
from clarity_backend.database import engine
from clarity_backend.notifications.crud import delete_account_tokens

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

_OAUTH_SUCCESS_HTML = """<!DOCTYPE html>
<html><head><title>Connected</title>
<style>
  body {{ font-family: system-ui, sans-serif; display: flex; align-items: center;
         justify-content: center; height: 100vh; margin: 0; background: #fdf6e3; }}
  .card {{ border: 4px solid #000; background: #fff; padding: 2.5rem;
           box-shadow: 8px 8px 0 #000; text-align: center; max-width: 400px; }}
  h2 {{ margin: 0 0 0.5rem; font-weight: 900; text-transform: uppercase; }}
  p {{ color: #666; font-size: 0.875rem; margin: 0; }}
  .email {{ font-family: monospace; font-weight: bold; color: #000; }}
</style></head>
<body><div class="card">
  <div style="font-size:3rem;margin-bottom:1rem">&#x2705;</div>
  <h2>{service} Connected</h2>
  <p class="email">{email}</p>
  <p style="margin-top:1rem">You can close this window.</p>
</div>
<script>setTimeout(function(){{ window.close(); }}, 2000);</script>
</body></html>"""


@router.get("/auth/google/start")
async def google_oauth_start():
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(500, "Google OAuth not configured")
    from clarity_backend.auth.google import build_auth_url

    return RedirectResponse(url=build_auth_url())


@router.get("/auth/google/callback")
async def google_oauth_callback(code: str, state: str = ""):
    from clarity_backend.auth.google import (
        exchange_code,
        get_user_email,
        save_tokens,
        validate_and_consume_state,
    )
    from clarity_backend.services.registry import registry

    code_verifier = validate_and_consume_state(state) if state else None
    if not code_verifier:
        raise HTTPException(400, "Invalid or expired state token")
    try:
        tokens = await exchange_code(code, code_verifier)
        email = await get_user_email(tokens["access_token"])
        await save_tokens(email, tokens)
        await registry.add_gmail_service(email, tokens)
        return HTMLResponse(_OAUTH_SUCCESS_HTML.format(service="Gmail", email=email))
    except Exception as e:
        logger.exception("Google OAuth callback failed")
        raise HTTPException(500, f"OAuth token exchange failed: {e}") from e


@router.delete("/api/auth/gmail/{email}")
async def remove_gmail_account(email: str):
    from sqlmodel.ext.asyncio.session import AsyncSession

    from clarity_backend.services.registry import registry

    removed = await registry.remove_gmail_service(email)
    async with AsyncSession(engine) as session:
        deleted = await delete_account_tokens(session, "gmail", email)
    if not removed and not deleted:
        raise HTTPException(404, f"No Gmail account found for {email}")
    return {"status": "removed", "email": email}


@router.get("/auth/microsoft/start")
async def microsoft_oauth_start():
    if not settings.MS_CLIENT_ID or not settings.MS_CLIENT_SECRET:
        raise HTTPException(500, "Microsoft OAuth not configured")
    from clarity_backend.auth.microsoft import build_auth_url

    return RedirectResponse(url=build_auth_url())


@router.get("/auth/microsoft/callback")
async def microsoft_oauth_callback(code: str, state: str = ""):
    from clarity_backend.auth.microsoft import (
        exchange_code,
        get_user_email,
        save_tokens,
        validate_and_consume_state,
    )
    from clarity_backend.services.registry import registry

    if not state or not validate_and_consume_state(state):
        raise HTTPException(400, "Invalid or expired state token")
    try:
        tokens = exchange_code(code)
        email = await get_user_email(tokens["access_token"])
        await save_tokens(email, tokens)
        await registry.add_outlook_service(email, tokens)
        return HTMLResponse(_OAUTH_SUCCESS_HTML.format(service="Outlook", email=email))
    except Exception as e:
        raise HTTPException(500, f"OAuth token exchange failed: {e}") from e


@router.delete("/api/auth/outlook/{email}")
async def remove_outlook_account(email: str):
    from sqlmodel.ext.asyncio.session import AsyncSession

    from clarity_backend.services.registry import registry

    removed = await registry.remove_outlook_service(email)
    async with AsyncSession(engine) as session:
        deleted = await delete_account_tokens(session, "outlook", email)
    if not removed and not deleted:
        raise HTTPException(404, f"No Outlook account found for {email}")
    return {"status": "removed", "email": email}
