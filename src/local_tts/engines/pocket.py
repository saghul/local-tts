from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

import numpy as np

from .base import TTSEngine, VoiceInfo, float32_to_int16

logger = logging.getLogger(__name__)

POCKET_VOICES = [
    VoiceInfo(id="alba", name="Alba", language="en", gender="female"),
    VoiceInfo(id="marius", name="Marius", language="en", gender="male"),
    VoiceInfo(id="javert", name="Javert", language="en", gender="male"),
    VoiceInfo(id="jean", name="Jean", language="en", gender="male"),
    VoiceInfo(id="fantine", name="Fantine", language="en", gender="female"),
    VoiceInfo(id="cosette", name="Cosette", language="en", gender="female"),
    VoiceInfo(id="eponine", name="Eponine", language="en", gender="female"),
    VoiceInfo(id="azelma", name="Azelma", language="en", gender="female"),
]


class PocketEngine:
    def __init__(self) -> None:
        self._model = None
        self._voice_states: dict[str, object] = {}

    @property
    def name(self) -> str:
        return "pocket"

    def list_voices(self) -> list[VoiceInfo]:
        return list(POCKET_VOICES)

    def _ensure_model(self):
        if self._model is not None:
            return
        from pocket_tts import TTSModel

        logger.info("Loading Pocket TTS model...")
        self._model = TTSModel.load_model()
        logger.info("Pocket TTS model loaded")

    def _get_voice_state(self, voice_id: str):
        if voice_id not in self._voice_states:
            self._ensure_model()
            self._voice_states[voice_id] = self._model.get_state_for_audio_prompt(voice_id)
        return self._voice_states[voice_id]

    def _generate_sync(self, text: str, voice_id: str, speed: float) -> list[np.ndarray]:
        self._ensure_model()
        voice_state = self._get_voice_state(voice_id)
        chunks = []
        for audio_tensor in self._model.generate_audio_stream(voice_state, text):
            audio_np = audio_tensor.cpu().numpy()
            # Pocket TTS outputs float audio, convert to int16
            chunks.append(float32_to_int16(audio_np))
        return chunks

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
