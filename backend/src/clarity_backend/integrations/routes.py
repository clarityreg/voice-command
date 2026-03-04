import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.config import settings
from clarity_backend.database import get_session
from clarity_backend.integrations.plane import PlaneClient, severity_to_priority
from clarity_backend.models import TriageItem

router = APIRouter(prefix="/api/triage", tags=["triage-actions"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("/{item_id}/create-issue", status_code=status.HTTP_201_CREATED)
async def create_plane_issue(item_id: int, session: SessionDep) -> dict:
    """Create a Plane work item from a triage item and mark it as actioned."""
    result = await session.exec(select(TriageItem).where(TriageItem.id == item_id))
    item = result.first()

    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Triage item not found")

    priority = severity_to_priority(item.severity)

    source_prefix = "[PostHog]" if item.source == "posthog" else "[Aikido]"
    title = f"{source_prefix} {item.title}"

    metadata = json.loads(item.metadata_json) if item.metadata_json else {}
    description_html = f"<p>{item.description}</p><pre>{json.dumps(metadata, indent=2)}</pre>"

    labels = ["bug", f"{item.source}-auto"]

    plane_client = PlaneClient(
        api_key=settings.PLANE_API_KEY,
        workspace_slug=settings.PLANE_WORKSPACE_SLUG,
        project_id=settings.PLANE_PROJECT_ID,
    )

    issue_data = await plane_client.create_work_item(
        title=title,
        description_html=description_html,
        priority=priority,
        labels=labels,
    )

    # Update triage item: mark as actioned, store issue URL in metadata
    metadata["plane_issue_url"] = issue_data.get("url", "")
    metadata["plane_issue_id"] = issue_data.get("id", "")
    item.metadata_json = json.dumps(metadata)
    item.status = "actioned"
    session.add(item)
    await session.commit()

    return issue_data
