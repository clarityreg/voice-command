"""Plane task management routes — projects, tasks, and action confirmation."""

from fastapi import APIRouter
from pydantic import BaseModel

from clarity_backend.config import settings as env_settings
from clarity_backend.integrations.plane import PlaneClient
from clarity_backend.settings.manager import _read_settings, get_plane_projects

router = APIRouter(prefix="/api/plane", tags=["plane"])


def _get_client() -> PlaneClient:
    s = _read_settings()
    api_key = s.get("plane_api_key") or env_settings.PLANE_API_KEY
    workspace = s.get("plane_workspace_slug") or env_settings.PLANE_WORKSPACE_SLUG
    return PlaneClient(
        api_key=api_key,
        workspace_slug=workspace,
        base_url=env_settings.PLANE_API_URL,
    )


@router.get("/projects")
async def list_projects() -> dict:
    projects = get_plane_projects()
    return {"projects": projects}


@router.get("/projects/{project_id}/tasks")
async def list_tasks(project_id: str, assignees: str = "me") -> dict:
    client = _get_client()
    try:
        items = await client.list_work_items(project_id, assignees=assignees)
        return {"tasks": items}
    except Exception as e:
        return {"error": str(e), "tasks": []}


@router.get("/projects/{project_id}/states")
async def get_project_states(project_id: str) -> dict:
    client = _get_client()
    try:
        states = await client.get_states(project_id)
        return {"states": states}
    except Exception as e:
        return {"error": str(e), "states": []}


class ConfirmActionRequest(BaseModel):
    action_type: str  # "create_task" or "complete_task"
    project_id: str
    project_name: str | None = None
    # For create_task:
    title: str | None = None
    priority: str | None = None
    # For complete_task:
    issue_id: str | None = None
    state_id: str | None = None
    task_ref: str | None = None


@router.post("/confirm-action")
async def confirm_action(body: ConfirmActionRequest) -> dict:
    client = _get_client()

    if body.action_type == "create_task":
        if not body.title:
            return {"error": "Title is required.", "response": "Task title is missing."}
        priority = body.priority or "none"
        try:
            result = await client.create_work_item(
                title=body.title,
                description_html="<p>Created via Clarity voice command</p>",
                priority=priority,
                labels=[],
                project_id=body.project_id,
            )
            seq = result.get("sequence_id", "")
            identifier = result.get("project_detail", {}).get("identifier", "")
            ref = f"{identifier}-{seq}" if identifier and seq else str(seq)
            return {
                "response": f"Created task {ref}: {body.title}",
                "issue": result,
            }
        except Exception as e:
            return {"error": str(e), "response": f"Failed to create task: {e}"}

    elif body.action_type == "complete_task":
        if not body.issue_id:
            return {"error": "Issue ID is required.", "response": "Issue ID is missing."}

        # Find the Done state if no state_id provided
        state_id = body.state_id
        if not state_id:
            s = _read_settings()
            done_name = s.get("plane_done_state_name", "Done")
            try:
                states = await client.get_states(body.project_id)
                for st in states:
                    if st.get("name", "").lower() == done_name.lower():
                        state_id = st["id"]
                        break
                if not state_id:
                    return {
                        "error": f"No state named '{done_name}' found.",
                        "response": f"Could not find a '{done_name}' state in this project.",
                    }
            except Exception as e:
                return {"error": str(e), "response": f"Failed to fetch states: {e}"}

        try:
            result = await client.update_work_item_state(
                project_id=body.project_id,
                issue_id=body.issue_id,
                state_id=state_id,
            )
            name = result.get("name", body.task_ref or body.issue_id)
            return {"response": f"Completed task: {name}", "issue": result}
        except Exception as e:
            return {"error": str(e), "response": f"Failed to complete task: {e}"}

    return {"error": f"Unknown action type: {body.action_type}", "response": "Unknown action."}
