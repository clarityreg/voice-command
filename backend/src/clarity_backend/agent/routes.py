"""Agent API routes — create and manage AI-driven fix jobs."""

import json
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.database import engine, get_session
from clarity_backend.models import TriageItem, utcnow

from .models import AgentJob
from .runner import CLAUDE_CLI_AVAILABLE, create_plan, execute_plan

router = APIRouter(prefix="/api/agent", tags=["agent"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@asynccontextmanager
async def get_background_session():
    """Session factory for BackgroundTasks (can't use Depends)."""
    async with AsyncSession(engine) as session:
        yield session


def _job_to_dict(job: AgentJob) -> dict:
    return {
        "id": job.id,
        "triage_item_id": job.triage_item_id,
        "status": job.status,
        "plan_text": job.plan_text,
        "result_summary": job.result_summary,
        "branch_name": job.branch_name,
        "error_message": job.error_message,
        "events": json.loads(job.events_json),
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


@router.post("/fix/{item_id}")
async def start_fix(
    item_id: int,
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> dict:
    """Create an AgentJob for the given triage item and start planning."""
    if not CLAUDE_CLI_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Claude CLI not installed. Install from https://claude.ai/download",
        )
    item = await session.get(TriageItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Triage item not found")

    # Capture item attributes before commit expires the instance
    item_dict = {
        "title": item.title,
        "description": item.description,
        "severity": item.severity,
        "source": item.source,
    }

    job = AgentJob(triage_item_id=item_id)
    session.add(job)
    await session.commit()
    await session.refresh(job)

    background_tasks.add_task(create_plan, job.id, get_background_session, item_dict)

    return {"job_id": job.id, "status": job.status}


@router.get("/jobs")
async def list_jobs(session: SessionDep) -> list[dict]:
    """List the 50 most recent agent jobs."""
    result = await session.exec(
        select(AgentJob).order_by(AgentJob.created_at.desc()).limit(50)  # type: ignore[attr-defined]
    )
    return [_job_to_dict(job) for job in result.all()]


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, session: SessionDep) -> dict:
    """Fetch a single agent job by ID."""
    job = await session.get(AgentJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Agent job not found")
    return _job_to_dict(job)


@router.post("/jobs/{job_id}/approve")
async def approve_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> dict:
    """Approve a plan_ready job and begin execution."""
    job = await session.get(AgentJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Agent job not found")
    if job.status != "plan_ready":
        raise HTTPException(
            status_code=400, detail=f"Job is in '{job.status}' state, expected 'plan_ready'"
        )

    job.status = "approved"
    job.updated_at = utcnow()
    session.add(job)
    await session.commit()

    background_tasks.add_task(execute_plan, job.id, get_background_session)

    return {"job_id": job.id, "status": job.status}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, session: SessionDep) -> dict:
    """Cancel a job that hasn't completed yet."""
    job = await session.get(AgentJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Agent job not found")
    if job.status in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel a job in '{job.status}' state")

    job.status = "cancelled"
    job.updated_at = utcnow()
    session.add(job)
    await session.commit()

    return {"job_id": job.id, "status": job.status}
