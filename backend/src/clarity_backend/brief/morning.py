from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.database import get_session
from clarity_backend.models import TriageItem

router = APIRouter(prefix="/api/brief", tags=["brief"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


class MorningBriefResponse(BaseModel):
    new_errors_24h: int
    new_vulns_24h: int
    actioned_yesterday: int
    pending_total: int
    top_severity: str | None


@router.get("/morning")
async def morning_brief(session: SessionDep) -> MorningBriefResponse:
    now = datetime.now(UTC).replace(tzinfo=None)
    yesterday = now - timedelta(hours=24)

    # New errors (posthog) in last 24h
    errors_result = await session.exec(
        select(func.count()).where(
            TriageItem.source == "posthog",
            TriageItem.first_seen >= yesterday,
        )
    )
    new_errors = errors_result.one()

    # New vulnerabilities (aikido) in last 24h
    vulns_result = await session.exec(
        select(func.count()).where(
            TriageItem.source == "aikido",
            TriageItem.first_seen >= yesterday,
        )
    )
    new_vulns = vulns_result.one()

    # Actioned in last 24h
    actioned_result = await session.exec(
        select(func.count()).where(
            TriageItem.status == "actioned",
            TriageItem.last_seen >= yesterday,
        )
    )
    actioned_yesterday = actioned_result.one()

    # Total pending
    pending_result = await session.exec(
        select(func.count()).where(TriageItem.status == "pending")
    )
    pending_total = pending_result.one()

    # Top severity among pending items
    top_severity = None
    for sev in ["critical", "high", "medium", "low"]:
        sev_result = await session.exec(
            select(func.count()).where(
                TriageItem.severity == sev,
                TriageItem.status == "pending",
            )
        )
        if sev_result.one() > 0:
            top_severity = sev
            break

    return MorningBriefResponse(
        new_errors_24h=new_errors,
        new_vulns_24h=new_vulns,
        actioned_yesterday=actioned_yesterday,
        pending_total=pending_total,
        top_severity=top_severity,
    )
