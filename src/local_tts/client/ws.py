from __future__ import annotations

import base64
import json
from typing import AsyncIterator

import numpy as np
import websockets


class TTSWebSocketClient:
    def __init__(self, server_url: str, voice_id: str, model_id: str) -> None:
        self.server_url = server_url
        self.voice_id = voice_id
        self.model_id = model_id
        self._ws = None

    async def connect(self) -> None:
        url = (
            f"{self.server_url}/v1/text-to-speech/{self.voice_id}/stream-input"
            f"?model_id={self.model_id}&output_format=pcm_24000"
        )
        self._ws = await websockets.connect(url)

    async def synthesize(self, text: str, speed: float = 1.0) -> AsyncIterator[np.ndarray]:
        """Send text and yield audio chunks."""
        if self._ws is None:
            raise RuntimeError("Not connected")

        # BOS
        bos = {"text": " ", "voice_settings": {"speed": speed}}
        await self._ws.send(json.dumps(bos))

        # Text
        await self._ws.send(json.dumps({"text": text}))

        # EOS
        await self._ws.send(json.dumps({"text": ""}))

        # Receive audio
        while True:
            raw = await self._ws.recv()
            msg = json.loads(raw)
            if msg.get("isFinal"):
                break
            audio_bytes = base64.b64decode(msg["audio"])
            yield np.frombuffer(audio_bytes, dtype=np.int16)

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
