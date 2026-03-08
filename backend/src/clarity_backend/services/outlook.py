import asyncio
from datetime import datetime

import httpx

from clarity_backend.notifications.models import Notification, NotificationType, Source
from clarity_backend.services.base import BaseService


class OutlookService(BaseService):
    GRAPH_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(self, account_email: str, credentials: dict | None = None):
        super().__init__(Source.OUTLOOK, account_email)
        self.email = account_email
        self._credentials = credentials
        self._access_token: str | None = None
        self._delta_link: str | None = None
        self._poll_interval = 30

    async def connect(self) -> bool:
        try:
            if not self._credentials:
                from clarity_backend.auth.microsoft import load_tokens

                self._credentials = await load_tokens(self.email)
            if self._credentials:
                self._access_token = self._credentials.get("access_token")
                return self._access_token is not None
            return False
        except Exception as e:
            print(f"[Outlook] Connection error: {e}")
            return False

    async def disconnect(self):
        self._access_token = None

    async def fetch_recent(self, limit: int = 20) -> list[Notification]:
        if not self._access_token:
            return []
        notifications = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self.GRAPH_BASE}/me/mailFolders/inbox/messages",
                    headers={"Authorization": f"Bearer {self._access_token}"},
                    params={
                        "$top": limit,
                        "$orderby": "receivedDateTime desc",
                        "$select": "id,subject,bodyPreview,from,receivedDateTime,isRead,conversationId",
                    },
                )
                resp.raise_for_status()
                for msg in resp.json().get("value", []):
                    notifications.append(self._message_to_notification(msg))
        except Exception as e:
            print(f"[Outlook] Error fetching recent: {e}")
        return notifications

    async def listen(self):
        while self._running:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    if self._delta_link:
                        url = self._delta_link
                        params = {}
                    else:
                        url = f"{self.GRAPH_BASE}/me/mailFolders/inbox/messages/delta"
                        params = {
                            "$select": "id,subject,bodyPreview,from,receivedDateTime,isRead,conversationId"
                        }

                    resp = await client.get(
                        url,
                        headers={"Authorization": f"Bearer {self._access_token}"},
                        params=params,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    for msg in data.get("value", []):
                        await self.emit_notification(self._message_to_notification(msg))
                    self._delta_link = data.get("@odata.deltaLink")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    await self.connect()
                else:
                    raise
            except Exception as e:
                print(f"[Outlook] Polling error: {e}")
            await asyncio.sleep(self._poll_interval)

    async def reply(self, source_id: str, body: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.GRAPH_BASE}/me/messages/{source_id}/reply",
                    headers={
                        "Authorization": f"Bearer {self._access_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "message": {"body": {"contentType": "Text", "content": body}},
                        "comment": body,
                    },
                )
                resp.raise_for_status()
                return True
        except Exception as e:
            print(f"[Outlook] Reply error: {e}")
            return False

    async def add_category(self, message_id: str, category: str = "Clarity - Actioned") -> bool:
        """Add a category to an Outlook message."""
        if not self._access_token:
            return False
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self.GRAPH_BASE}/me/messages/{message_id}",
                    headers={"Authorization": f"Bearer {self._access_token}"},
                    params={"$select": "categories"},
                )
                resp.raise_for_status()
                existing = resp.json().get("categories", [])
                if category in existing:
                    return True
                resp = await client.patch(
                    f"{self.GRAPH_BASE}/me/messages/{message_id}",
                    headers={
                        "Authorization": f"Bearer {self._access_token}",
                        "Content-Type": "application/json",
                    },
                    json={"categories": [*existing, category]},
                )
                resp.raise_for_status()
                return True
        except Exception as e:
            print(f"[Outlook] Error adding category: {e}")
            return False

    def _message_to_notification(self, msg: dict) -> Notification:
        from_data = msg.get("from", {}).get("emailAddress", {})
        return Notification(
            source=Source.OUTLOOK,
            source_account=self.account,
            source_id=msg["id"],
            notification_type=NotificationType.EMAIL,
            title=msg.get("subject", "(No Subject)"),
            body=msg.get("bodyPreview", ""),
            sender_name=from_data.get("name", from_data.get("address", "Unknown")),
            thread_id=msg.get("conversationId"),
            timestamp=datetime.fromisoformat(
                msg.get("receivedDateTime", datetime.utcnow().isoformat()).replace(
                    "Z", "+00:00"
                )
            ),
            raw_payload={"isRead": msg.get("isRead", False)},
        )
