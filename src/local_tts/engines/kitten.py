from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

import numpy as np

from .base import VoiceInfo, float32_to_int16

logger = logging.getLogger(__name__)

KITTEN_MODEL_SIZES = {
    "mini": "KittenML/kitten-tts-mini-0.8",
    "micro": "KittenML/kitten-tts-micro-0.8",
    "nano": "KittenML/kitten-tts-nano-0.8",
    "nano-int8": "KittenML/kitten-tts-nano-0.8-int8",
}

KITTEN_VOICES = [
    VoiceInfo(id="bella", name="Bella", language="en", gender="female"),
    VoiceInfo(id="jasper", name="Jasper", language="en", gender="male"),
    VoiceInfo(id="luna", name="Luna", language="en", gender="female"),
    VoiceInfo(id="bruno", name="Bruno", language="en", gender="male"),
    VoiceInfo(id="rosie", name="Rosie", language="en", gender="female"),
    VoiceInfo(id="hugo", name="Hugo", language="en", gender="male"),
    VoiceInfo(id="kiki", name="Kiki", language="en", gender="female"),
    VoiceInfo(id="leo", name="Leo", language="en", gender="male"),
]


class KittenEngine:
    def __init__(self, model_size: str = "micro") -> None:
        if model_size not in KITTEN_MODEL_SIZES:
            raise ValueError(
                f"Unknown KittenTTS model size: {model_size!r}. "
                f"Available: {', '.join(KITTEN_MODEL_SIZES)}"
            )
        self._model_size = model_size
        self._model_name = KITTEN_MODEL_SIZES[model_size]
        self._model = None

    @property
    def name(self) -> str:
        return "kitten"

    def list_voices(self) -> list[VoiceInfo]:
        return list(KITTEN_VOICES)

    def _ensure_model(self):
        if self._model is not None:
            return
        from kittentts import KittenTTS

        logger.info("Loading KittenTTS model (%s)...", self._model_name)
        self._model = KittenTTS(self._model_name)
        logger.info("KittenTTS model loaded")

    def _generate_sync(self, text: str, voice_id: str, speed: float) -> list[np.ndarray]:
        self._ensure_model()
        # KittenTTS expects capitalized voice names
        voice_name = voice_id.capitalize()
        audio = self._model.generate(text, voice=voice_name, speed=speed)
        audio = np.asarray(audio, dtype=np.float32)
        return [float32_to_int16(audio)]

    def warmup(self) -> None:
        self._ensure_model()

    async def generate_audio_stream(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
    ) -> AsyncIterator[np.ndarray]:
        loop = asyncio.get_running_loop()
        chunks = await loop.run_in_executor(
            None, self._generate_sync, text, voice_id, speed
        )
        for chunk in chunks:
            yield chunk
