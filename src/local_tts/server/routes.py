from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..engines.registry import get_registry
from .models import ModelResponse, TTSRequest, VoiceResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/v1/text-to-speech/{voice_id}/stream")
async def stream_tts(
    voice_id: str,
    request: TTSRequest,
    output_format: str = Query(default="pcm_24000"),
):
    registry = get_registry()
    try:
        engine = registry.get(request.model_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    speed = request.voice_settings.speed if request.voice_settings else 1.0

    async def audio_generator():
        try:
            async for chunk in engine.generate_audio_stream(
                text=request.text,
                voice_id=voice_id,
                speed=speed,
            ):
                yield chunk.tobytes()
        except Exception:
            logger.exception("Audio generation error")
            raise

    return StreamingResponse(
        audio_generator(),
        media_type="application/octet-stream",
        headers={"Content-Type": "audio/pcm;rate=24000;encoding=signed-int;bits=16"},
    )


@router.get("/v1/voices")
async def list_voices(model_id: str = Query(default="kokoro")):
    registry = get_registry()
    try:
        engine = registry.get(model_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return [
        VoiceResponse(voice_id=v.id, name=v.name, category=v.gender)
        for v in engine.list_voices()
    ]


@router.get("/v1/models")
async def list_models():
    registry = get_registry()
    return [
        ModelResponse(model_id=m["model_id"], name=m["name"])
        for m in registry.list_models()
    ]
