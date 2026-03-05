import asyncio
from datetime import UTC, datetime

from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.web.async_client import AsyncWebClient

from clarity_backend.notifications.models import Notification, NotificationType, Priority, Source
from clarity_backend.services.base import BaseService


class SlackService(BaseService):
    def __init__(self, workspace_name: str, bot_token: str, app_token: str):
        super().__init__(Source.SLACK, workspace_name)
        self.workspace_name = workspace_name
        self._bot_token = bot_token
        self._app_token = app_token
        self._web_client: AsyncWebClient | None = None
        self._socket_client: SocketModeClient | None = None
        self._user_cache: dict[str, str] = {}
        self._channel_cache: dict[str, str] = {}
        self._event_handler: object | None = None

    async def connect(self) -> bool:
        try:
            self._web_client = AsyncWebClient(token=self._bot_token)
            self._socket_client = SocketModeClient(
                app_token=self._app_token, web_client=self._web_client
            )
            auth = await self._web_client.auth_test()
            if auth["ok"]:
                return True
            return False
        except Exception as e:
            print(f"[Slack] Connection error for {self.workspace_name}: {e}")
            return False

    async def disconnect(self):
        if self._socket_client:
            if self._event_handler in self._socket_client.socket_mode_request_listeners:
                self._socket_client.socket_mode_request_listeners.remove(self._event_handler)
            await self._socket_client.close()

    async def fetch_recent(self, limit: int = 20) -> list[Notification]:
        if not self._web_client:
            return []
        notifications = []
        try:
            # Fetch DMs
            try:
                dm_convos = await self._web_client.conversations_list(
                    types="im,mpim", limit=10
                )
            except Exception:
                dm_convos = await self._web_client.conversations_list(
                    types="im", limit=10
                )

            for conv in dm_convos.get("channels", [])[:5]:
                await self._fetch_channel_messages(conv["id"], notifications, is_dm=True)

            # Fetch public channels the bot is a member of
            try:
                chan_convos = await self._web_client.conversations_list(
                    types="public_channel,private_channel", limit=20
                )
                member_channels = [
                    c for c in chan_convos.get("channels", []) if c.get("is_member")
                ]
                for conv in member_channels[:10]:
                    await self._fetch_channel_messages(conv["id"], notifications, is_dm=False)
            except Exception:
                pass

        except Exception as e:
            print(f"[Slack] Error fetching recent for {self.workspace_name}: {e}")
        notifications.sort(key=lambda n: n.timestamp, reverse=True)
        return notifications[:limit]

    async def _fetch_channel_messages(
        self, channel_id: str, notifications: list, is_dm: bool = False
    ):
        try:
            history = await self._web_client.conversations_history(
                channel=channel_id, limit=3
            )
            for msg in history.get("messages", []):
                if msg.get("subtype") is None:
                    notification = await self._message_to_notification(
                        msg, channel_id, is_dm=is_dm
                    )
                    if notification:
                        notifications.append(notification)
        except Exception:
            pass

    async def listen(self):
        async def handle_event(client: SocketModeClient, req: SocketModeRequest):
            response = SocketModeResponse(envelope_id=req.envelope_id)
            await client.send_socket_mode_response(response)
            if req.type == "events_api":
                event = req.payload.get("event", {})
                event_type = event.get("type")
                if event_type == "message" and not event.get("subtype"):
                    channel_id = event.get("channel")
                    notification = await self._message_to_notification(event, channel_id)
                    if notification:
                        await self.emit_notification(notification)
                elif event_type == "app_mention":
                    channel_id = event.get("channel")
                    notification = await self._message_to_notification(
                        event, channel_id, is_mention=True
                    )
                    if notification:
                        notification.notification_type = NotificationType.MENTION
                        notification.priority = Priority.HIGH
                        await self.emit_notification(notification)

        self._event_handler = handle_event
        self._socket_client.socket_mode_request_listeners.append(handle_event)
        await self._socket_client.connect()
        while self._running:
            await asyncio.sleep(1)

    async def reply(self, source_id: str, body: str) -> bool:
        raise NotImplementedError("Slack is configured as read-only")

    async def _resolve_user(self, user_id: str) -> str:
        if user_id in self._user_cache:
            return self._user_cache[user_id]
        try:
            info = await self._web_client.users_info(user=user_id)
            name = info["user"]["profile"].get("display_name") or info["user"]["real_name"]
            self._user_cache[user_id] = name
            return name
        except Exception:
            return user_id

    async def _resolve_channel(self, channel_id: str) -> str:
        if channel_id in self._channel_cache:
            return self._channel_cache[channel_id]
        try:
            info = await self._web_client.conversations_info(channel=channel_id)
            name = info["channel"].get("name", channel_id)
            self._channel_cache[channel_id] = name
            return name
        except Exception:
            return channel_id

    async def _message_to_notification(
        self,
        msg: dict,
        channel_id: str,
        is_dm: bool = False,
        is_mention: bool = False,
    ) -> Notification | None:
        try:
            user_id = msg.get("user", "unknown")
            sender_name = await self._resolve_user(user_id)
            channel_name = await self._resolve_channel(channel_id)
            text = msg.get("text", "")
            ntype = NotificationType.MENTION if is_mention else NotificationType.MESSAGE
            ts = msg.get("ts", "")
            thread_ts = msg.get("thread_ts", ts)

            return Notification(
                source=Source.SLACK,
                source_account=self.workspace_name,
                source_id=f"{channel_id}:{thread_ts}",
                notification_type=ntype,
                title=(
                    f"{'@mention in' if is_mention else ''} #{channel_name}"
                    if not is_dm
                    else f"DM from {sender_name}"
                ),
                body=text[:500],
                sender_name=sender_name,
                channel_name=channel_name,
                thread_id=thread_ts if thread_ts != ts else None,
                timestamp=datetime.fromtimestamp(float(ts), tz=UTC) if ts else datetime.now(tz=UTC),
                priority=Priority.HIGH if is_mention else Priority.NORMAL,
                is_actionable=False,
                raw_payload={"channel_id": channel_id, "ts": ts},
            )
        except Exception as e:
            print(f"[Slack] Error parsing message: {e}")
            return None
