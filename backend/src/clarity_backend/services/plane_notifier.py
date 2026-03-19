import asyncio
from datetime import datetime

import httpx

from clarity_backend.config import settings
from clarity_backend.notifications.models import Notification, NotificationType, Priority, Source
from clarity_backend.services.base import BaseService


class PlaneNotifierService(BaseService):
    def __init__(self):
        super().__init__(Source.PLANE, "Plane")
        self._base_url = settings.PLANE_API_URL.rstrip("/")
        self._headers = {
            "X-API-Key": settings.PLANE_API_KEY,
            "Content-Type": "application/json",
        }
        self._workspace = settings.PLANE_WORKSPACE_SLUG
        self._poll_interval = 30
        self._last_check: datetime | None = None

    @property
    def _configured(self) -> bool:
        return bool(settings.PLANE_API_KEY and self._workspace and settings.PLANE_PROJECT_ID)

    async def connect(self) -> bool:
        if not self._configured:
            print("[Plane] Skipping — API key, workspace, or project ID not set")
            return False
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self._base_url}/workspaces/{self._workspace}/projects/",
                    headers=self._headers,
                )
                resp.raise_for_status()
                return True
        except Exception as e:
            print(f"[Plane] Connection error: {e}")
            return False

    async def disconnect(self):
        pass

    async def fetch_recent(self, limit: int = 20) -> list[Notification]:
        notifications = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self._base_url}/workspaces/{self._workspace}/projects/{settings.PLANE_PROJECT_ID}/issues/",
                    headers=self._headers,
                    params={
                        "assignees": "me",
                        "order_by": "-updated_at",
                        "per_page": limit,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                issues = data.get("results", data) if isinstance(data, dict) else data
                if isinstance(issues, list):
                    for issue in issues[:limit]:
                        notifications.append(self._issue_to_notification(issue))
        except Exception as e:
            print(f"[Plane] Error fetching issues: {e}")
        return notifications

    async def listen(self):
        if not self._configured:
            return
        while self._running:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    params = {
                        "assignees": "me",
                        "order_by": "-updated_at",
                        "per_page": 10,
                    }
                    if self._last_check:
                        params["updated_at__gte"] = self._last_check.isoformat()
                    resp = await client.get(
                        f"{self._base_url}/workspaces/{self._workspace}/projects/{settings.PLANE_PROJECT_ID}/issues/",
                        headers=self._headers,
                        params=params,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    issues = data.get("results", data) if isinstance(data, dict) else data
                    if isinstance(issues, list):
                        for issue in issues:
                            await self.emit_notification(self._issue_to_notification(issue))
                    self._last_check = datetime.utcnow()
            except Exception as e:
                print(f"[Plane] Polling error: {e}")
            await asyncio.sleep(self._poll_interval)

    async def create_issue(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        project_id: str | None = None,
    ) -> dict | None:
        try:
            proj = project_id or settings.PLANE_PROJECT_ID
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self._base_url}/workspaces/{self._workspace}/projects/{proj}/issues/",
                    headers=self._headers,
                    json={
                        "name": title,
                        "description_html": f"<p>{description}</p>",
                        "priority": priority,
                    },
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            print(f"[Plane] Error creating issue: {e}")
            return None

    def _issue_to_notification(self, issue: dict) -> Notification:
        priority_map = {
            "urgent": Priority.URGENT,
            "high": Priority.HIGH,
            "medium": Priority.NORMAL,
            "low": Priority.LOW,
            "none": Priority.LOW,
        }
        priority = priority_map.get(issue.get("priority", "medium"), Priority.NORMAL)
        return Notification(
            source=Source.PLANE,
            source_account="Plane",
            source_id=str(issue.get("id", "")),
            notification_type=NotificationType.TASK_UPDATE,
            title=issue.get("name", "Untitled Issue"),
            body=issue.get("description_stripped", issue.get("description", ""))[:300],
            sender_name="Plane",
            project_name=issue.get("project_detail", {}).get("name", ""),
            priority=priority,
            timestamp=datetime.fromisoformat(
                issue.get("updated_at", datetime.utcnow().isoformat()).replace("Z", "+00:00")
            ),
            raw_payload={
                "state": issue.get("state_detail", {}).get("name"),
                "sequence_id": issue.get("sequence_id"),
                "labels": [label.get("name") for label in issue.get("label_detail", [])],
            },
        )
