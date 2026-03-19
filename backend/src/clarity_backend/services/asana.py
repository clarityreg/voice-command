import asyncio
from datetime import datetime

import httpx

from clarity_backend.config import settings
from clarity_backend.notifications.models import Notification, NotificationType, Priority, Source
from clarity_backend.services.base import BaseService


class AsanaService(BaseService):
    BASE_URL = "https://app.asana.com/api/1.0"

    def __init__(self):
        super().__init__(Source.ASANA, "Asana")
        self._headers = {
            "Authorization": f"Bearer {settings.ASANA_ACCESS_TOKEN}",
            "Accept": "application/json",
        }
        self._poll_interval = 30
        self._last_check: datetime | None = None

    async def connect(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{self.BASE_URL}/users/me", headers=self._headers)
                resp.raise_for_status()
                user = resp.json()["data"]
                print(f"[Asana] Authenticated as {user['name']}")
                return True
        except Exception as e:
            print(f"[Asana] Connection error: {e}")
            return False

    async def disconnect(self):
        pass

    async def fetch_recent(self, limit: int = 20) -> list[Notification]:
        notifications = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/tasks",
                    headers=self._headers,
                    params={
                        "assignee": "me",
                        "workspace": settings.ASANA_DEFAULT_WORKSPACE_GID,
                        "opt_fields": "name,notes,due_on,completed,created_at,modified_at,projects.name",
                        "completed_since": "now",
                        "limit": limit,
                    },
                )
                resp.raise_for_status()
                for task in resp.json()["data"]:
                    notifications.append(self._task_to_notification(task))
        except Exception as e:
            print(f"[Asana] Error fetching tasks: {e}")
        return notifications

    async def listen(self):
        while self._running:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    params = {
                        "assignee": "me",
                        "workspace": settings.ASANA_DEFAULT_WORKSPACE_GID,
                        "opt_fields": "name,notes,due_on,completed,created_at,modified_at,projects.name",
                        "completed_since": "now",
                        "limit": 10,
                    }
                    if self._last_check:
                        params["modified_since"] = self._last_check.isoformat()
                    resp = await client.get(
                        f"{self.BASE_URL}/tasks", headers=self._headers, params=params
                    )
                    resp.raise_for_status()
                    for task in resp.json()["data"]:
                        await self.emit_notification(self._task_to_notification(task))
                    self._last_check = datetime.utcnow()
            except Exception as e:
                print(f"[Asana] Polling error: {e}")
            await asyncio.sleep(self._poll_interval)

    async def create_task(
        self, title: str, description: str = "", project_gid: str | None = None
    ) -> dict | None:
        try:
            project = project_gid or settings.ASANA_DEFAULT_PROJECT_GID
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.BASE_URL}/tasks",
                    headers={**self._headers, "Content-Type": "application/json"},
                    json={
                        "data": {
                            "name": title,
                            "notes": description,
                            "projects": [project],
                            "workspace": settings.ASANA_DEFAULT_WORKSPACE_GID,
                        }
                    },
                )
                resp.raise_for_status()
                return resp.json()["data"]
        except Exception as e:
            print(f"[Asana] Error creating task: {e}")
            return None

    def _task_to_notification(self, task: dict) -> Notification:
        projects = [p["name"] for p in task.get("projects", [])]
        project_name = projects[0] if projects else "No Project"
        priority = Priority.NORMAL
        if task.get("due_on"):
            due = datetime.strptime(task["due_on"], "%Y-%m-%d")
            days_until = (due - datetime.utcnow()).days
            if days_until < 0:
                priority = Priority.URGENT
            elif days_until <= 2:
                priority = Priority.HIGH
        return Notification(
            source=Source.ASANA,
            source_account="Asana",
            source_id=task["gid"],
            notification_type=NotificationType.TASK_UPDATE,
            title=task.get("name", "Untitled Task"),
            body=task.get("notes", "")[:300],
            sender_name="Asana",
            project_name=project_name,
            priority=priority,
            timestamp=datetime.fromisoformat(
                task.get("modified_at", datetime.utcnow().isoformat()).replace("Z", "+00:00")
            ),
            raw_payload={
                "due_on": task.get("due_on"),
                "completed": task.get("completed"),
            },
        )
