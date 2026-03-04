"""Shared OAuth token persistence for all providers."""

from datetime import datetime

from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.database import engine
from clarity_backend.models import TokenStore


async def save_tokens(service: str, email: str, tokens: dict) -> None:
    token_id = f"{service}:{email}"
    async with AsyncSession(engine) as session:
        existing = await session.get(TokenStore, token_id)
        if existing:
            existing.access_token = tokens["access_token"]
            existing.refresh_token = tokens.get("refresh_token") or existing.refresh_token
            if tokens.get("expires_at"):
                existing.expires_at = datetime.fromisoformat(tokens["expires_at"])
            session.add(existing)
        else:
            record = TokenStore(
                id=token_id,
                service=service,
                account=email,
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token", ""),
                expires_at=(
                    datetime.fromisoformat(tokens["expires_at"])
                    if tokens.get("expires_at")
                    else None
                ),
            )
            session.add(record)
        await session.commit()


async def load_tokens(service: str, email: str) -> dict | None:
    token_id = f"{service}:{email}"
    async with AsyncSession(engine) as session:
        record = await session.get(TokenStore, token_id)
        if not record:
            return None
        return {
            "access_token": record.access_token,
            "refresh_token": record.refresh_token,
        }
