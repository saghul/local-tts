from __future__ import annotations

import base64
import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from ..engines.registry import get_registry
from .models import WSAudioMessage, WSTextMessage

logger = logging.getLogger(__name__)

ws_router = APIRouter()


@ws_router.websocket("/v1/text-to-speech/{voice_id}/stream-input")
async def websocket_tts(
    websocket: WebSocket,
    voice_id: str,
    model_id: str = Query(default="kokoro"),
    output_format: str = Query(default="pcm_24000"),
):
    await websocket.accept()
    registry = get_registry()

    try:
        engine = registry.get(model_id)
    except ValueError as e:
        await websocket.close(code=1003, reason=str(e))
        return

    try:
        speed = 1.0
        accumulated_text: list[str] = []

        while True:
            raw = await websocket.receive_text()
            msg = WSTextMessage.model_validate_json(raw)

            # BOS message
            if msg.text == " ":
                accumulated_text = []
                if msg.voice_settings:
                    speed = msg.voice_settings.speed
                continue

            # EOS message - generate audio for accumulated text
            if msg.text == "":
                if accumulated_text:
                    full_text = "".join(accumulated_text)
                    async for chunk in engine.generate_audio_stream(
                        text=full_text,
                        voice_id=voice_id,
                        speed=speed,
                    ):
                        audio_b64 = base64.b64encode(chunk.tobytes()).decode()
                        resp = WSAudioMessage(audio=audio_b64, isFinal=False)
                        await websocket.send_text(resp.model_dump_json())

                # Send final message
                final = WSAudioMessage(isFinal=True)
                await websocket.send_text(final.model_dump_json())
                accumulated_text = []
                continue

            # Regular text message
            accumulated_text.append(msg.text)

            # If flush requested, generate immediately
            if msg.flush:
                full_text = "".join(accumulated_text)
                async for chunk in engine.generate_audio_stream(
                    text=full_text,
                    voice_id=voice_id,
                    speed=speed,
                ):
                    audio_b64 = base64.b64encode(chunk.tobytes()).decode()
                    resp = WSAudioMessage(audio=audio_b64, isFinal=False)
                    await websocket.send_text(resp.model_dump_json())
                accumulated_text = []

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception:
        logger.exception("WebSocket error")
        try:
            await websocket.close(code=1011, reason="Internal error")
        except Exception:
            pass
