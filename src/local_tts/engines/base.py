from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Protocol

import numpy as np


SAMPLE_RATE = 24000


@dataclass
class VoiceInfo:
    id: str
    name: str
    language: str
    gender: str


class TTSEngine(Protocol):
    @property
    def name(self) -> str: ...

    def list_voices(self) -> list[VoiceInfo]: ...

    async def generate_audio_stream(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
    ) -> AsyncIterator[np.ndarray]:
        """Yield chunks of int16 PCM audio at 24kHz."""
        ...


def float32_to_int16(audio: np.ndarray) -> np.ndarray:
    """Convert float32 audio [-1, 1] to int16 PCM."""
    audio = np.clip(audio, -1.0, 1.0)
    return (audio * 32767).astype(np.int16)
