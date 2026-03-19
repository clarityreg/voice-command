from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from clarity_backend.agent.routes import router as agent_router
from clarity_backend.auth.routes import router as auth_router
from clarity_backend.brief.morning import router as brief_router
from clarity_backend.config import settings
from clarity_backend.database import init_db
from clarity_backend.integrations.routes import router as integrations_router
from clarity_backend.notifications.routes import router as notification_router
from clarity_backend.plane.routes import router as plane_router
from clarity_backend.settings.manager import router as settings_router
from clarity_backend.stats.routes import router as stats_router
from clarity_backend.triage.routes import router as triage_router
from clarity_backend.triage.unified import router as unified_triage_router
from clarity_backend.voice.router import router as voice_router
from clarity_backend.webhooks.aikido import router as aikido_router
from clarity_backend.webhooks.clarity import router as clarity_webhook_router
from clarity_backend.webhooks.posthog import router as posthog_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_db()
    try:
        from clarity_backend.services.registry import registry

        await registry.start_all()
    except Exception as e:
        print(f"[Startup] Notification services error (non-fatal): {e}")
    yield
    try:
        from clarity_backend.services.registry import registry

        await registry.stop_all()
    except Exception:
        pass


app = FastAPI(title="Clarity Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_origins_list != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(posthog_router)
app.include_router(aikido_router)
app.include_router(triage_router)
app.include_router(integrations_router)
app.include_router(brief_router)
app.include_router(settings_router)
app.include_router(voice_router)
app.include_router(stats_router)
app.include_router(notification_router)
app.include_router(auth_router)
app.include_router(unified_triage_router)
app.include_router(agent_router)
app.include_router(plane_router)
app.include_router(clarity_webhook_router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    from sqlmodel.ext.asyncio.session import AsyncSession

    from clarity_backend.database import engine
    from clarity_backend.notifications.crud import load_notifications
    from clarity_backend.notifications.models import WebSocketMessage
    from clarity_backend.notifications.ws import ws_manager

    await ws_manager.connect(websocket)
    try:
        async with AsyncSession(engine) as session:
            notifications_data = await load_notifications(session, limit=100)
        initial_msg = WebSocketMessage(
            event="initial_load", data={"notifications": notifications_data}
        )
        await websocket.send_text(initial_msg.model_dump_json())
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
