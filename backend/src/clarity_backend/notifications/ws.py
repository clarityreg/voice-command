import asyncio

from fastapi import WebSocket

from clarity_backend.notifications.models import Notification, WebSocketMessage


class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: WebSocketMessage):
        data = message.model_dump_json()
        dead: set[WebSocket] = set()

        async def _send(conn: WebSocket) -> None:
            try:
                await conn.send_text(data)
            except Exception:
                dead.add(conn)

        await asyncio.gather(*[_send(c) for c in self.active_connections])
        self.active_connections -= dead

    async def send_notification(self, notification: Notification):
        msg = WebSocketMessage(
            event="new_notification",
            data=notification.model_dump(mode="json"),
        )
        await self.broadcast(msg)

    async def send_update(self, notification_id: str, updates: dict):
        msg = WebSocketMessage(
            event="notification_updated",
            data={"id": notification_id, **updates},
        )
        await self.broadcast(msg)

    async def send_connection_status(self, service: str, connected: bool, account: str = ""):
        msg = WebSocketMessage(
            event="connection_status",
            data={"service": service, "connected": connected, "account": account},
        )
        await self.broadcast(msg)


ws_manager = ConnectionManager()
