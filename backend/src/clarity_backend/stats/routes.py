"""Statistics API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.database import get_session
from clarity_backend.stats.queries import (
    avg_time_to_triage_hours,
    daily_actioned_trend,
    get_severity_breakdown,
    weekly_resolved_count,
)

router = APIRouter(prefix="/api", tags=["stats"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


class TrendPoint(BaseModel):
    date: str
    count: int


class StatsResponse(BaseModel):
    weekly_resolved: int
    avg_triage_hours: float | None
    trend: list[TrendPoint]
    severity_breakdown: dict[str, int]


@router.get("/stats")
async def get_stats(session: SessionDep) -> StatsResponse:
    weekly = await weekly_resolved_count(session)
    avg_hours = await avg_time_to_triage_hours(session)
    trend = await daily_actioned_trend(session)
    breakdown = await get_severity_breakdown(session)

    return StatsResponse(
        weekly_resolved=weekly,
        avg_triage_hours=avg_hours,
        trend=[TrendPoint(**p) for p in trend],
        severity_breakdown=breakdown,
    )
