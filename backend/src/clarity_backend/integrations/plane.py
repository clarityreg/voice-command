import httpx

SEVERITY_PRIORITY_MAP = {
    "critical": "urgent",
    "high": "high",
    "medium": "medium",
    "low": "low",
}


def severity_to_priority(severity: str) -> str:
    return SEVERITY_PRIORITY_MAP.get(severity, "low")


class PlaneClient:
    def __init__(
        self,
        api_key: str,
        workspace_slug: str,
        project_id: str = "",
        base_url: str = "https://plane-api.clarityregulatory.work",
    ) -> None:
        self.api_key = api_key
        self.workspace_slug = workspace_slug
        self.project_id = project_id
        # Strip trailing /api/v1 if present — _ws_url adds it
        cleaned = base_url.rstrip("/")
        if cleaned.endswith("/api/v1"):
            cleaned = cleaned[: -len("/api/v1")]
        self.base_url = cleaned

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def _ws_url(self, path: str) -> str:
        return f"{self.base_url}/api/v1/workspaces/{self.workspace_slug}{path}"

    async def create_work_item(
        self,
        title: str,
        description_html: str,
        priority: str,
        labels: list[str],
        project_id: str | None = None,
    ) -> dict:
        proj = project_id or self.project_id
        url = self._ws_url(f"/projects/{proj}/issues/")
        body = {
            "name": title,
            "description_html": description_html,
            "priority": priority,
            "labels": labels,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers, json=body)
            response.raise_for_status()
            return response.json()

    async def list_projects(self) -> list[dict]:
        url = self._ws_url("/projects/")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers)
            response.raise_for_status()
            data = response.json()
            return data.get("results", data) if isinstance(data, dict) else data

    async def get_states(self, project_id: str) -> list[dict]:
        url = self._ws_url(f"/projects/{project_id}/states/")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers)
            response.raise_for_status()
            data = response.json()
            return data.get("results", data) if isinstance(data, dict) else data

    async def list_work_items(
        self,
        project_id: str,
        assignees: str = "me",
        limit: int = 20,
    ) -> list[dict]:
        url = self._ws_url(f"/projects/{project_id}/issues/")
        params: dict[str, str | int] = {
            "assignees": assignees,
            "order_by": "-updated_at",
            "per_page": limit,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers, params=params)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", data) if isinstance(data, dict) else data
            return results if isinstance(results, list) else []

    async def update_work_item_state(
        self,
        project_id: str,
        issue_id: str,
        state_id: str,
    ) -> dict:
        url = self._ws_url(f"/projects/{project_id}/issues/{issue_id}/")
        body = {"state": state_id}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(url, headers=self._headers, json=body)
            response.raise_for_status()
            return response.json()

    async def get_work_item_by_sequence(
        self,
        project_id: str,
        sequence_id: int,
    ) -> dict | None:
        url = self._ws_url(f"/projects/{project_id}/issues/")
        params = {"search": str(sequence_id), "per_page": 5}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers, params=params)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", data) if isinstance(data, dict) else data
            if isinstance(results, list):
                for item in results:
                    if item.get("sequence_id") == sequence_id:
                        return item
            return None
