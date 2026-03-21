import logging
import urllib.parse

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from clarity_backend.config import settings
from clarity_backend.database import engine
from clarity_backend.notifications.crud import delete_account_tokens

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


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

    base = settings.OAUTH_REDIRECT_BASE
    code_verifier = validate_and_consume_state(state) if state else None
    if not code_verifier:
        msg = urllib.parse.quote("Invalid or expired state token")
        return RedirectResponse(
            url=f"{base}/auth/callback?provider=gmail&status=error&message={msg}",
            status_code=302,
        )
    try:
        tokens = await exchange_code(code, code_verifier)
        email = await get_user_email(tokens["access_token"])
        await save_tokens(email, tokens)
        await registry.add_gmail_service(email, tokens)
        encoded_email = urllib.parse.quote(email)
        return RedirectResponse(
            url=f"{base}/auth/callback?provider=gmail&email={encoded_email}&status=success",
            status_code=302,
        )
    except Exception as e:
        logger.exception("Google OAuth callback failed")
        msg = urllib.parse.quote(f"OAuth token exchange failed: {e}")
        return RedirectResponse(
            url=f"{base}/auth/callback?provider=gmail&status=error&message={msg}",
            status_code=302,
        )


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

    base = settings.OAUTH_REDIRECT_BASE
    if not state or not validate_and_consume_state(state):
        msg = urllib.parse.quote("Invalid or expired state token")
        return RedirectResponse(
            url=f"{base}/auth/callback?provider=outlook&status=error&message={msg}",
            status_code=302,
        )
    try:
        tokens = exchange_code(code)
        email = await get_user_email(tokens["access_token"])
        await save_tokens(email, tokens)
        await registry.add_outlook_service(email, tokens)
        encoded_email = urllib.parse.quote(email)
        return RedirectResponse(
            url=f"{base}/auth/callback?provider=outlook&email={encoded_email}&status=success",
            status_code=302,
        )
    except Exception as e:
        logger.exception("Microsoft OAuth callback failed")
        msg = urllib.parse.quote(f"OAuth token exchange failed: {e}")
        return RedirectResponse(
            url=f"{base}/auth/callback?provider=outlook&status=error&message={msg}",
            status_code=302,
        )


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
