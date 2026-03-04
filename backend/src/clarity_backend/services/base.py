import asyncio
import contextlib
from abc import ABC, abstractmethod

from clarity_backend.notifications.models import Notification, Source
from clarity_backend.notifications.ws import ws_manager


class BaseService(ABC):
    def __init__(self, source: Source, account: str):
        self.source = source
        self.account = account
        self._running = False
        self._task: asyncio.Task | None = None

    @abstractmethod
    async def connect(self) -> bool:
        pass

    @abstractmethod
    async def disconnect(self):
        pass

    @abstractmethod
    async def fetch_recent(self, limit: int = 20) -> list[Notification]:
        pass

    @abstractmethod
    async def listen(self):
        pass

    @property
    def is_connected(self) -> bool:
        return self._running

    async def reply(self, source_id: str, body: str) -> bool:
        raise NotImplementedError(f"{self.source.value} does not support replies")

    async def start(self):
        connected = await self.connect()
        if connected:
            self._running = True
            self._task = asyncio.create_task(self._run_listener())
            await ws_manager.send_connection_status(self.source.value, True, self.account)
            print(f"[{self.source.value}] Connected: {self.account}")
        else:
            await ws_manager.send_connection_status(self.source.value, False, self.account)
            print(f"[{self.source.value}] Failed to connect: {self.account}")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        await self.disconnect()
        await ws_manager.send_connection_status(self.source.value, False, self.account)

    async def _run_listener(self):
        while self._running:
            try:
                await self.listen()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[{self.source.value}] Error in listener ({self.account}): {e}")
                await ws_manager.send_connection_status(self.source.value, False, self.account)
                await asyncio.sleep(5)
                if self._running:
                    print(f"[{self.source.value}] Reconnecting {self.account}...")
                    await self.connect()

    async def emit_notification(self, notification: Notification):
        from sqlmodel.ext.asyncio.session import AsyncSession

        from clarity_backend.database import engine
        from clarity_backend.notifications.crud import save_notification

        async with AsyncSession(engine) as session:
            await save_notification(session, notification)
        await ws_manager.send_notification(notification)
