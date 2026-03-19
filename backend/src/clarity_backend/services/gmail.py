import asyncio
import base64
import contextlib
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from clarity_backend.config import settings
from clarity_backend.notifications.models import Notification, NotificationType, Source
from clarity_backend.services.base import BaseService


class GmailService(BaseService):
    def __init__(self, account_email: str, credentials: dict | None = None):
        super().__init__(Source.GMAIL, account_email)
        self.email = account_email
        self._credentials = credentials
        self._gmail_client = None
        self._last_history_id: str | None = None
        self._seen_ids: set[str] = set()
        self._actioned_label_id: str | None = None
        self._poll_interval = 30

    async def connect(self) -> bool:
        try:
            if not self._credentials:
                from clarity_backend.auth.google import load_tokens

                self._credentials = await load_tokens(self.email)
            if not self._credentials:
                return False

            creds = Credentials(
                token=self._credentials.get("access_token"),
                refresh_token=self._credentials.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
            )
            if creds.expired and creds.refresh_token:
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: creds.refresh(Request())
                )
                from clarity_backend.auth.google import save_tokens

                await save_tokens(
                    self.email,
                    {
                        "access_token": creds.token,
                        "refresh_token": creds.refresh_token,
                        "expires_at": creds.expiry.isoformat() if creds.expiry else None,
                    },
                )

            self._gmail_client = build("gmail", "v1", credentials=creds)
            return True
        except Exception as e:
            print(f"[Gmail] Connection error for {self.email}: {e}")
            return False

    async def disconnect(self):
        self._gmail_client = None

    async def fetch_recent(self, limit: int = 20) -> list[Notification]:
        if not self._gmail_client:
            return []
        notifications = []
        try:
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: (
                    self._gmail_client.users()
                    .messages()
                    .list(userId="me", maxResults=limit, q="is:inbox")
                    .execute()
                ),
            )
            for msg_ref in results.get("messages", []):
                msg_id = msg_ref["id"]
                self._seen_ids.add(msg_id)
                notification = await self._message_to_notification(msg_id)
                if notification:
                    notifications.append(notification)

            if not self._last_history_id:
                profile = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._gmail_client.users().getProfile(userId="me").execute(),
                )
                self._last_history_id = str(profile.get("historyId", ""))
        except Exception as e:
            print(f"[Gmail] Error fetching recent for {self.email}: {e}")
        return notifications

    async def listen(self):
        while self._running:
            try:
                if self._last_history_id:
                    await self._poll_incremental()
                else:
                    await self._poll_full()
            except Exception as e:
                print(f"[Gmail] Polling error for {self.email}: {e}")
            await asyncio.sleep(self._poll_interval)

    async def _poll_incremental(self):
        try:
            history_id = self._last_history_id
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: (
                    self._gmail_client.users()
                    .history()
                    .list(
                        userId="me",
                        startHistoryId=history_id,
                        historyTypes=["messageAdded"],
                    )
                    .execute()
                ),
            )
            new_history_id = results.get("historyId")
            if new_history_id:
                self._last_history_id = str(new_history_id)

            for record in results.get("history", []):
                for added in record.get("messagesAdded", []):
                    msg_id = added["message"]["id"]
                    labels = added["message"].get("labelIds", [])
                    if msg_id not in self._seen_ids and "INBOX" in labels:
                        self._seen_ids.add(msg_id)
                        notification = await self._message_to_notification(msg_id)
                        if notification:
                            await self.emit_notification(notification)
        except Exception as e:
            if "404" in str(e) or "historyid" in str(e).lower():
                self._last_history_id = None
            else:
                raise

    async def _poll_full(self):
        results = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: (
                self._gmail_client.users()
                .messages()
                .list(userId="me", maxResults=10, q="is:inbox is:unread")
                .execute()
            ),
        )
        for msg_ref in results.get("messages", []):
            msg_id = msg_ref["id"]
            if msg_id not in self._seen_ids:
                self._seen_ids.add(msg_id)
                notification = await self._message_to_notification(msg_id)
                if notification:
                    await self.emit_notification(notification)

        profile = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._gmail_client.users().getProfile(userId="me").execute(),
        )
        self._last_history_id = str(profile.get("historyId", ""))

    async def reply(self, source_id: str, body: str) -> bool:
        try:
            original = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: (
                    self._gmail_client.users()
                    .messages()
                    .get(
                        userId="me",
                        id=source_id,
                        format="metadata",
                        metadataHeaders=["Subject", "From", "To", "Message-ID"],
                    )
                    .execute()
                ),
            )
            headers = {
                h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])
            }
            thread_id = original.get("threadId")
            reply_to = headers.get("From", "")
            subject = headers.get("Subject", "")
            if not subject.startswith("Re: "):
                subject = f"Re: {subject}"

            message_body = (
                f"To: {reply_to}\r\nSubject: {subject}\r\n"
                f"In-Reply-To: {headers.get('Message-ID', '')}\r\n\r\n{body}"
            )
            encoded = base64.urlsafe_b64encode(message_body.encode()).decode()
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: (
                    self._gmail_client.users()
                    .messages()
                    .send(userId="me", body={"raw": encoded, "threadId": thread_id})
                    .execute()
                ),
            )
            return True
        except Exception as e:
            print(f"[Gmail] Reply error: {e}")
            return False

    async def _ensure_actioned_label(self) -> str | None:
        """Create 'Clarity/Actioned' label if it doesn't exist, return label ID."""
        if self._actioned_label_id:
            return self._actioned_label_id
        if not self._gmail_client:
            return None
        try:
            labels = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._gmail_client.users().labels().list(userId="me").execute(),
            )
            for label in labels.get("labels", []):
                if label["name"] == "Clarity/Actioned":
                    self._actioned_label_id = label["id"]
                    return label["id"]
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: (
                    self._gmail_client.users()
                    .labels()
                    .create(
                        userId="me",
                        body={
                            "name": "Clarity/Actioned",
                            "labelListVisibility": "labelShow",
                            "messageListVisibility": "show",
                        },
                    )
                    .execute()
                ),
            )
            self._actioned_label_id = result["id"]
            return result["id"]
        except Exception as e:
            print(f"[Gmail] Error ensuring actioned label: {e}")
            return None

    async def add_label(self, message_id: str) -> bool:
        """Add the 'Clarity/Actioned' label to a Gmail message."""
        if not self._gmail_client:
            return False
        try:
            label_id = await self._ensure_actioned_label()
            if not label_id:
                return False
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: (
                    self._gmail_client.users()
                    .messages()
                    .modify(userId="me", id=message_id, body={"addLabelIds": [label_id]})
                    .execute()
                ),
            )
            return True
        except Exception as e:
            print(f"[Gmail] Error adding label: {e}")
            return False

    async def _message_to_notification(self, message_id: str) -> Notification | None:
        try:
            msg = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: (
                    self._gmail_client.users()
                    .messages()
                    .get(
                        userId="me",
                        id=message_id,
                        format="metadata",
                        metadataHeaders=["Subject", "From", "Date"],
                    )
                    .execute()
                ),
            )
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            snippet = msg.get("snippet", "")
            from_header = headers.get("From", "Unknown")
            sender_name = from_header.split("<")[0].strip().strip('"')
            timestamp = datetime.now(tz=UTC)
            date_str = headers.get("Date")
            if date_str:
                with contextlib.suppress(ValueError, TypeError):
                    timestamp = parsedate_to_datetime(date_str)

            return Notification(
                source=Source.GMAIL,
                source_account=self.email,
                source_id=message_id,
                notification_type=NotificationType.EMAIL,
                title=headers.get("Subject", "(No Subject)"),
                body=snippet,
                sender_name=sender_name,
                thread_id=msg.get("threadId"),
                timestamp=timestamp,
                raw_payload={"labels": msg.get("labelIds", [])},
            )
        except Exception as e:
            print(f"[Gmail] Error parsing message {message_id}: {e}")
            return None
