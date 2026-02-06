from __future__ import annotations

import asyncio
import logging
import os
from typing import AsyncIterator

import numpy as np

from .base import SAMPLE_RATE, TTSEngine, VoiceInfo, float32_to_int16

logger = logging.getLogger(__name__)

# All Kokoro voices (American English subset for default)
KOKORO_VOICES = [
    VoiceInfo(id="af_heart", name="Heart", language="en-us", gender="female"),
    VoiceInfo(id="af_alloy", name="Alloy", language="en-us", gender="female"),
    VoiceInfo(id="af_aoede", name="Aoede", language="en-us", gender="female"),
    VoiceInfo(id="af_bella", name="Bella", language="en-us", gender="female"),
    VoiceInfo(id="af_jessica", name="Jessica", language="en-us", gender="female"),
    VoiceInfo(id="af_kore", name="Kore", language="en-us", gender="female"),
    VoiceInfo(id="af_nicole", name="Nicole", language="en-us", gender="female"),
    VoiceInfo(id="af_nova", name="Nova", language="en-us", gender="female"),
    VoiceInfo(id="af_river", name="River", language="en-us", gender="female"),
    VoiceInfo(id="af_sarah", name="Sarah", language="en-us", gender="female"),
    VoiceInfo(id="af_sky", name="Sky", language="en-us", gender="female"),
    VoiceInfo(id="am_adam", name="Adam", language="en-us", gender="male"),
    VoiceInfo(id="am_echo", name="Echo", language="en-us", gender="male"),
    VoiceInfo(id="am_eric", name="Eric", language="en-us", gender="male"),
    VoiceInfo(id="am_fenrir", name="Fenrir", language="en-us", gender="male"),
    VoiceInfo(id="am_liam", name="Liam", language="en-us", gender="male"),
    VoiceInfo(id="am_michael", name="Michael", language="en-us", gender="male"),
    VoiceInfo(id="am_onyx", name="Onyx", language="en-us", gender="male"),
    VoiceInfo(id="am_puck", name="Puck", language="en-us", gender="male"),
    VoiceInfo(id="am_santa", name="Santa", language="en-us", gender="male"),
    VoiceInfo(id="bf_alice", name="Alice", language="en-gb", gender="female"),
    VoiceInfo(id="bf_emma", name="Emma", language="en-gb", gender="female"),
    VoiceInfo(id="bf_isabella", name="Isabella", language="en-gb", gender="female"),
    VoiceInfo(id="bf_lily", name="Lily", language="en-gb", gender="female"),
    VoiceInfo(id="bm_daniel", name="Daniel", language="en-gb", gender="male"),
    VoiceInfo(id="bm_fable", name="Fable", language="en-gb", gender="male"),
    VoiceInfo(id="bm_george", name="George", language="en-gb", gender="male"),
    VoiceInfo(id="bm_lewis", name="Lewis", language="en-gb", gender="male"),
]


class KokoroEngine:
    def __init__(self) -> None:
        self._pipeline = None

    @property
    def name(self) -> str:
        return "kokoro"

    def list_voices(self) -> list[VoiceInfo]:
        return list(KOKORO_VOICES)

    def _ensure_pipeline(self):
        if self._pipeline is not None:
            return
        os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
        from kokoro import KPipeline

        logger.info("Loading Kokoro pipeline...")
        self._pipeline = KPipeline(lang_code="a")
        logger.info("Kokoro pipeline loaded")

    def _generate_sync(self, text: str, voice_id: str, speed: float) -> list[np.ndarray]:
        self._ensure_pipeline()
        chunks = []
        for _graphemes, _phonemes, audio in self._pipeline(
            text, voice=voice_id, speed=speed
        ):
            # Kokoro yields torch.Tensor float32 — convert to numpy first
            audio_np = audio.cpu().numpy() if hasattr(audio, "numpy") else np.asarray(audio)
            chunks.append(float32_to_int16(audio_np))
        return chunks

    def warmup(self) -> None:
        self._ensure_pipeline()

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
