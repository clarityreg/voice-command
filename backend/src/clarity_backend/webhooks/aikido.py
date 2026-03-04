"""Aikido webhook receiver with HMAC-SHA256 signature verification."""

import hashlib
import hmac
import json
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.config import settings
from clarity_backend.database import get_session
from clarity_backend.models import TriageItem

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

REPLAY_WINDOW_SECONDS = 30

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _verify_signature(body: bytes, timestamp: str, signature: str) -> bool:
    expected = hmac.new(
        settings.AIKIDO_WEBHOOK_SECRET.encode(),
        f"{timestamp}.".encode() + body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/aikido", status_code=202)
async def aikido_webhook(
    request: Request,
    x_aikido_webhook_signature: Annotated[str, Header()],
    x_aikido_webhook_timestamp: Annotated[str, Header()],
    session: SessionDep,
) -> dict[str, str]:
    body = await request.body()

    # Replay protection
    try:
        ts = int(x_aikido_webhook_timestamp)
    except ValueError as err:
        raise HTTPException(status_code=401, detail="Invalid timestamp") from err

    if abs(time.time() - ts) > REPLAY_WINDOW_SECONDS:
        raise HTTPException(status_code=401, detail="Request too old")

    # Signature verification
    if not _verify_signature(body, x_aikido_webhook_timestamp, x_aikido_webhook_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(body)
    vuln = payload.get("vulnerability", {})

    cve = vuln.get("cve", "")
    vuln_id = vuln.get("id", "")
    fingerprint = cve if cve else vuln_id

    title = vuln.get("title", vuln_id or "Unknown vulnerability")
    description = vuln.get("description", "")
    remediation = vuln.get("remediation", "")
    if remediation:
        description = f"{description}\n\nRemediation: {remediation}".strip()

    severity = vuln.get("severity", "low").lower()

    metadata = {
        "cve": cve,
        "package_name": vuln.get("package_name", ""),
        "package_version": vuln.get("package_version", ""),
        "event_type": payload.get("event_type", ""),
    }

    item = TriageItem(
        source="aikido",
        title=title,
        description=description,
        severity=severity,
        fingerprint=fingerprint,
        metadata_json=json.dumps(metadata),
    )
    session.add(item)
    await session.commit()

    return {"status": "accepted"}
