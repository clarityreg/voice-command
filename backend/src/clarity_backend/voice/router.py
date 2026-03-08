"""Voice processing API — accepts text or audio, classifies intent, executes command."""

import io
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from clarity_backend.database import get_session
from clarity_backend.voice.commands import execute
from clarity_backend.voice.intent import UNKNOWN, classify

router = APIRouter(prefix="/api/voice", tags=["voice"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


class VoiceRequest(BaseModel):
    text: str


class VoiceResponse(BaseModel):
    intent: dict
    response: str
    data: dict


class TranscribeResponse(BaseModel):
    text: str


def _get_openai_key() -> str:
    from clarity_backend.config import settings as env_settings
    from clarity_backend.settings.manager import _read_settings

    s = _read_settings()
    return s.get("openai_api_key") or env_settings.OPENAI_API_KEY


def _get_whisper_prompt() -> str:
    """Build a prompt hint with project names to improve transcription accuracy."""
    from clarity_backend.settings.manager import get_plane_projects

    projects = get_plane_projects()
    if not projects:
        return ""

    # Include aliases, names, and identifiers for maximum recognition
    terms: set[str] = set()
    for alias, info in projects.items():
        terms.add(alias)
        if name := info.get("name"):
            terms.add(name)
        if ident := info.get("identifier"):
            terms.add(ident)

    return "Project names: " + ", ".join(sorted(terms))


@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)) -> TranscribeResponse:
    """Transcribe audio using OpenAI Whisper API with project-name hints."""
    api_key = _get_openai_key()
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key not configured. Set it in Settings.",
        )

    audio_bytes = await audio.read()
    prompt = _get_whisper_prompt()

    # Determine filename extension from content type
    ext = "webm"
    if audio.content_type:
        type_map = {"audio/wav": "wav", "audio/webm": "webm", "audio/mp4": "mp4", "audio/ogg": "ogg"}
        ext = type_map.get(audio.content_type, "webm")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (f"audio.{ext}", io.BytesIO(audio_bytes), audio.content_type or "audio/webm")},
            data={"model": "whisper-1", "language": "en", **({"prompt": prompt} if prompt else {})},
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"OpenAI Whisper API error: {resp.text[:200]}",
            )

        text = resp.json().get("text", "").strip()

    return TranscribeResponse(text=text)


@router.post("/process-audio")
async def process_audio(session: SessionDep, audio: UploadFile = File(...)) -> VoiceResponse:
    """Transcribe audio via OpenAI Whisper and then process the voice command."""
    transcript = await transcribe_audio(audio)
    text = transcript.text

    if not text:
        return VoiceResponse(
            intent={"type": "unknown", "confidence": 0.0, "params": {}},
            response="Didn't catch that. Try again.",
            data={},
        )

    intent = classify(text)

    if intent.type == UNKNOWN and intent.confidence == 0.0:
        try:
            from clarity_backend.settings.manager import get_plane_projects
            from clarity_backend.voice.ai_classifier import classify_with_ai

            project_names = list(get_plane_projects().keys())
            ai_intent = await classify_with_ai(text, project_names)
            if ai_intent and ai_intent.confidence > 0.5:
                intent = ai_intent
        except Exception:
            pass

    result = await execute(intent, session)
    return VoiceResponse(
        intent=intent.to_dict(),
        response=result["response"],
        data=result.get("data", {}),
    )


@router.post("/process")
async def process_voice(body: VoiceRequest, session: SessionDep) -> VoiceResponse:
    intent = classify(body.text)

    # Tier 2: AI fallback when regex returns UNKNOWN
    if intent.type == UNKNOWN and intent.confidence == 0.0:
        try:
            from clarity_backend.settings.manager import get_plane_projects
            from clarity_backend.voice.ai_classifier import classify_with_ai

            project_names = list(get_plane_projects().keys())
            ai_intent = await classify_with_ai(body.text, project_names)
            if ai_intent and ai_intent.confidence > 0.5:
                intent = ai_intent
        except Exception:
            pass  # AI fallback is best-effort

    result = await execute(intent, session)
    return VoiceResponse(
        intent=intent.to_dict(),
        response=result["response"],
        data=result.get("data", {}),
    )
