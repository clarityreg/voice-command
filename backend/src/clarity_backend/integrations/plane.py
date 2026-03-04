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
        project_id: str,
        base_url: str = "https://plane-api.clarityregulatory.work",
    ) -> None:
        self.api_key = api_key
        self.workspace_slug = workspace_slug
        self.project_id = project_id
        self.base_url = base_url.rstrip("/")

    async def create_work_item(
        self,
        title: str,
        description_html: str,
        priority: str,
        labels: list[str],
    ) -> dict:
        url = (
            f"{self.base_url}/api/v1/workspaces/{self.workspace_slug}"
            f"/projects/{self.project_id}/issues/"
        )
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        body = {
            "name": title,
            "description_html": description_html,
            "priority": priority,
            "labels": labels,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            return response.json()
