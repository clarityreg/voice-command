"""Voice processing API — accepts text, classifies intent, executes command."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.database import get_session
from clarity_backend.voice.commands import execute
from clarity_backend.voice.intent import classify

router = APIRouter(prefix="/api/voice", tags=["voice"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


class VoiceRequest(BaseModel):
    text: str


class VoiceResponse(BaseModel):
    intent: dict
    response: str
    data: dict


@router.post("/process")
async def process_voice(body: VoiceRequest, session: SessionDep) -> VoiceResponse:
    intent = classify(body.text)
    result = await execute(intent, session)
    return VoiceResponse(
        intent=intent.to_dict(),
        response=result["response"],
        data=result.get("data", {}),
    )
