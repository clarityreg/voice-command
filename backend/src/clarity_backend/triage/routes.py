import json
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.database import get_session
from clarity_backend.models import TriageItem
from clarity_backend.triage.investigator import investigate
from clarity_backend.triage.patterns import get_recurring_fingerprints

router = APIRouter(prefix="/api", tags=["triage"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


class DismissRequest(BaseModel):
    reason: str = ""


class TriageStatusResponse(BaseModel):
    critical_count: int
    vulnerability_count: int
    actioned_today: int
    pending_count: int


@router.get("/triage")
async def list_triage_items(
    session: SessionDep,
    status: str | None = Query(None),
    source: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    query = select(TriageItem).order_by(TriageItem.last_seen.desc())  # type: ignore[attr-defined]
    if status:
        query = query.where(TriageItem.status == status)
    if source:
        query = query.where(TriageItem.source == source)
    query = query.offset(offset).limit(limit)
    result = await session.exec(query)
    items = result.all()
    recurring = await get_recurring_fingerprints(session)
    return [_item_to_dict(item, recurring) for item in items]


@router.post("/triage/{item_id}/snooze")
async def snooze_item(
    item_id: int,
    session: SessionDep,
) -> dict:
    item = await session.get(TriageItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Triage item not found")
    item.status = "snoozed"
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return _item_to_dict(item)


@router.post("/triage/{item_id}/dismiss")
async def dismiss_item(
    item_id: int,
    body: DismissRequest,
    session: SessionDep,
) -> dict:
    item = await session.get(TriageItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Triage item not found")
    item.status = "dismissed"
    metadata = json.loads(item.metadata_json)
    metadata["dismiss_reason"] = body.reason
    metadata["dismissed_at"] = datetime.now(UTC).isoformat()
    item.metadata_json = json.dumps(metadata)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return _item_to_dict(item)


@router.post("/triage/{item_id}/agent-fix")
async def start_agent_fix(
    item_id: int,
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> dict:
    item = await session.get(TriageItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Triage item not found")

    from clarity_backend.agent.models import AgentJob
    from clarity_backend.agent.routes import get_background_session
    from clarity_backend.agent.runner import create_plan

    job = AgentJob(triage_item_id=item_id)
    session.add(job)
    await session.commit()
    await session.refresh(job)

    item_dict = {
        "title": item.title,
        "description": item.description,
        "severity": item.severity,
        "source": item.source,
    }
    background_tasks.add_task(create_plan, job.id, get_background_session, item_dict)

    return {"job_id": job.id, "status": job.status}


@router.post("/triage/{item_id}/investigate")
async def investigate_item(
    item_id: int,
    session: SessionDep,
) -> dict:
    item = await session.get(TriageItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Triage item not found")

    metadata = json.loads(item.metadata_json)
    result = await investigate(
        title=item.title,
        description=item.description,
        severity=item.severity,
        source=item.source,
        metadata=metadata,
    )

    # Store investigation result in metadata
    metadata["investigation"] = result
    item.metadata_json = json.dumps(metadata)
    session.add(item)
    await session.commit()
    await session.refresh(item)

    return {
        "item_id": item_id,
        "investigation": result,
    }


@router.get("/status")
async def get_status(
    session: SessionDep,
) -> TriageStatusResponse:
    # Critical pending items
    critical_result = await session.exec(
        select(func.count()).where(
            TriageItem.severity == "critical",
            TriageItem.status == "pending",
        )
    )
    critical_count = critical_result.one()

    # Vulnerability (aikido) pending items
    vuln_result = await session.exec(
        select(func.count()).where(
            TriageItem.source == "aikido",
            TriageItem.status == "pending",
        )
    )
    vulnerability_count = vuln_result.one()

    # Actioned today
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    actioned_result = await session.exec(
        select(func.count()).where(
            TriageItem.status == "actioned",
            TriageItem.last_seen >= today_start,
        )
    )
    actioned_today = actioned_result.one()

    # Total pending
    pending_result = await session.exec(select(func.count()).where(TriageItem.status == "pending"))
    pending_count = pending_result.one()

    return TriageStatusResponse(
        critical_count=critical_count,
        vulnerability_count=vulnerability_count,
        actioned_today=actioned_today,
        pending_count=pending_count,
    )


def _item_to_dict(item: TriageItem, recurring: dict[str, int] | None = None) -> dict:
    is_recurring = bool(recurring and item.fingerprint in recurring)
    return {
        "id": item.id,
        "source": item.source,
        "title": item.title,
        "description": item.description,
        "severity": item.severity,
        "status": item.status,
        "fingerprint": item.fingerprint,
        "occurrence_count": item.occurrence_count,
        "first_seen": item.first_seen.isoformat() if item.first_seen else None,
        "last_seen": item.last_seen.isoformat() if item.last_seen else None,
        "metadata": json.loads(item.metadata_json),
        "recurring": is_recurring,
    }
