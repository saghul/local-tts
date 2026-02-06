from __future__ import annotations

from typing import Iterator

import httpx
import numpy as np


class TTSHTTPClient:
    """Streams PCM audio from the HTTP POST endpoint."""

    def __init__(self, server_url: str, voice_id: str, model_id: str) -> None:
        self.server_url = server_url.rstrip("/")
        self.voice_id = voice_id
        self.model_id = model_id

    def synthesize(self, text: str, speed: float = 1.0) -> Iterator[np.ndarray]:
        """POST text and yield int16 PCM chunks as they stream back."""
        url = f"{self.server_url}/v1/text-to-speech/{self.voice_id}/stream"
        body: dict = {"text": text, "model_id": self.model_id}
        if speed != 1.0:
            body["voice_settings"] = {"speed": speed}

        with httpx.stream(
            "POST",
            url,
            json=body,
            timeout=httpx.Timeout(connect=10, read=120, write=10, pool=10),
        ) as resp:
            resp.raise_for_status()
            for raw in resp.iter_bytes(chunk_size=4800):  # 100ms of int16 mono
                if raw:
                    yield np.frombuffer(raw, dtype=np.int16)
